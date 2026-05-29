import os
import json
import redis
import psycopg2
import numpy as np
from scipy.sparse import coo_matrix
from lightfm import LightFM

# 1. 데이터베이스(Redshift)에서 상호작용 매트릭스 로드
# 실환경에서는 Redshift Endpoint 정보 사용, 여기서는 환경변수로 주입받는 구조
REDSHIFT_HOST = os.getenv("REDSHIFT_HOST", "cosmetics-dw.redshift.amazonaws.com")
REDSHIFT_PORT = os.getenv("REDSHIFT_PORT", "5439")
REDSHIFT_DB = os.getenv("REDSHIFT_DB", "cosmetics_dw")
REDSHIFT_USER = os.getenv("REDSHIFT_USER", "awsuser")
REDSHIFT_PASSWORD = os.getenv("REDSHIFT_PASSWORD", "SecurePass123")

REDIS_HOST = os.getenv("REDIS_HOST", "cosmetics-cache.elasticache.amazonaws.com")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

def fetch_data_from_redshift():
    print("Fetching interactions data from Amazon Redshift...")
    # psycopg2를 사용해 Redshift 연결 및 쿼리 실행
    conn = psycopg2.connect(
        host=REDSHIFT_HOST,
        port=REDSHIFT_PORT,
        dbname=REDSHIFT_DB,
        user=REDSHIFT_USER,
        password=REDSHIFT_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, product_id, interaction_score FROM public.user_item_interactions")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def train_recommender(data):
    print("Preparing interaction matrix...")
    
    # 고유 유저 및 상품 인덱싱
    users = list(set([r[0] for r in data]))
    items = list(set([r[1] for r in data]))
    
    user_to_idx = {uid: idx for idx, uid in enumerate(users)}
    idx_to_user = {idx: uid for idx, uid in enumerate(users)}
    item_to_idx = {iid: idx for idx, iid in enumerate(items)}
    idx_to_item = {idx: iid for idx, iid in enumerate(items)}
    
    # COO Sparse Matrix 생성
    row_indices = [user_to_idx[r[0]] for r in data]
    col_indices = [item_to_idx[r[1]] for r in data]
    ratings = [float(r[2]) for r in data]
    
    interaction_matrix = coo_matrix(
        (ratings, (row_indices, col_indices)), 
        shape=(len(users), len(items))
    )
    
    print(f"Matrix shape: {interaction_matrix.shape}")
    print("Initializing LightFM Hybrid Model...")
    # WARP loss를 사용해 랭킹 최적화 모델 초기화
    model = LightFM(loss='warp', no_components=30, learning_rate=0.05)
    
    print("Fitting model...")
    model.fit(interaction_matrix, epochs=10, num_threads=2)
    
    return model, users, items, user_to_idx, idx_to_item

def generate_and_cache_recommendations(model, users, items, user_to_idx, idx_to_item):
    print("Connecting to Amazon ElastiCache (Redis)...")
    r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    
    n_users = len(users)
    n_items = len(items)
    item_ids = np.arange(n_items)
    
    print("Generating predictions and writing to Redis...")
    for user in users:
        u_idx = user_to_idx[user]
        
        # 유저에 대해 모든 상품의 스코어 예측
        scores = model.predict(u_idx, item_ids)
        
        # 예측 점수 내림차순 정렬 후 Top-5 추출
        top_indices = np.argsort(-scores)[:5]
        top_items = [idx_to_item[idx] for idx in top_indices]
        
        # Redis 적재 (Key: rec:user:{user_id}, Value: JSON string of item list)
        redis_key = f"rec:user:{user}"
        r_client.set(redis_key, json.dumps(top_items))
        
    print("Successfully cached all user recommendations to Redis.")

if __name__ == "__main__":
    try:
        data = fetch_data_from_redshift()
        # Mock 데이터 폴백 (DB 연결 실패 시 로컬 테스팅 목적)
        if not data:
            raise ValueError("No data returned from Redshift")
    except Exception as e:
        print(f"Database connection failed ({e}). Running with local mock data...")
        # Notion 명세의 유저수(943명), 상품수(1682개) 기준 임의 mock 데이터 생성
        np.random.seed(42)
        data = []
        for _ in range(5000):
            uid = f"user{np.random.randint(1, 944):04d}"
            pid = f"prod{np.random.randint(1, 1683):04d}"
            score = np.random.randint(1, 15)
            data.append((uid, pid, score))
            
    model, users, items, user_to_idx, idx_to_item = train_recommender(data)
    
    try:
        generate_and_cache_recommendations(model, users, items, user_to_idx, idx_to_item)
    except Exception as e:
        print(f"Could not connect to Redis ({e}). Printing sample recommendation for user0001:")
        scores = model.predict(user_to_idx["user0001"], np.arange(len(items)))
        top_indices = np.argsort(-scores)[:5]
        print(f"Top 5 products: {[idx_to_item[idx] for idx in top_indices]}")
