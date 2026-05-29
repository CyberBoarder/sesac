import os
import json
import redis
import psycopg2
import subprocess

# 로컬 DB 및 캐시 연동 설정 (docker-compose-local.yml 파일에 매핑)
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "cosmetics_dw"
DB_USER = "awsuser"
DB_PASS = "SecurePass123"

REDIS_HOST = "localhost"
REDIS_PORT = 6379

def seed_database():
    print("1. 로컬 PostgreSQL 데이터베이스 연결 및 테이블/모의 데이터 구성 시작...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cursor = conn.cursor()
    
    # Redshift 데이터 모델과 호환되는 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS public.user_item_interactions (
            user_id VARCHAR(50),
            product_id VARCHAR(50),
            interaction_score INT
        )
    """)
    
    # 기존 모의 데이터 청소
    cursor.execute("TRUNCATE TABLE public.user_item_interactions")
    
    # LightFM 모델 학습에 필요한 사용자-상품 상호작용 점수 모의 데이터 주입
    test_interactions = [
        ("user0001", "prod0001", 10),
        ("user0001", "prod0002", 5),
        ("user0001", "prod0003", 2),
        ("user0002", "prod0001", 8),
        ("user0002", "prod0004", 12),
        ("user0003", "prod0002", 4),
        ("user0003", "prod0005", 9),
        ("user0004", "prod0003", 7),
        ("user0004", "prod0004", 1),
        ("user0005", "prod0005", 15)
    ]
    
    # 모델 희소 행렬 차원 유실을 예방하기 위해 임의 유저/상품 20여개 쌍 루프 주입
    for i in range(1, 25):
        for j in range(1, 25):
            if (i+j) % 3 == 0:
                test_interactions.append((f"user{i:04d}", f"prod{j:04d}", (i*j)%10 + 1))
                
    for user_id, product_id, score in test_interactions:
        cursor.execute(
            "INSERT INTO public.user_item_interactions (user_id, product_id, interaction_score) VALUES (%s, %s, %s)",
            (user_id, product_id, score)
        )
        
    conn.commit()
    cursor.close()
    conn.close()
    print("   -> 모의 데이터베이스 구성 및 초기화 완료.")

def run_training_script():
    print("2. 로컬 환경 변수 주입 및 train_recommendation.py 호출...")
    # 실제 Redshift/ElastiCache 대신 로컬 컨테이너 주소를 환경변수로 세팅
    env = os.environ.copy()
    env["REDSHIFT_HOST"] = DB_HOST
    env["REDSHIFT_PORT"] = DB_PORT
    env["REDSHIFT_DB"] = DB_NAME
    env["REDSHIFT_USER"] = DB_USER
    env["REDSHIFT_PASSWORD"] = DB_PASS
    env["REDIS_HOST"] = REDIS_HOST
    env["REDIS_PORT"] = str(REDIS_PORT)
    
    # 서브프로세스를 통해 모델 빌드/적재 파이프라인 구동
    script_path = os.path.join(os.path.dirname(__file__), "train_recommendation.py")
    subprocess.run(["python", script_path], env=env, check=True)
    print("   -> 추천 모델 학습 및 캐시 적재 완료.")

def verify_redis_recommendations():
    print("3. 로컬 Redis 저장 결과 검증 조회 시작...")
    r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    
    test_user = "user0001"
    redis_key = f"rec:user:{test_user}"
    recommendations_json = r_client.get(redis_key)
    
    if recommendations_json:
        recommendations = json.loads(recommendations_json)
        print("==========================================================")
        print("성공: Redis에 탑-5 개인화 상품 추천 데이터가 저장되었습니다!")
        print(f"조회 Key  : {redis_key}")
        print(f"추천 상품 : {recommendations}")
        print("==========================================================")
    else:
        print(f"실패: {test_user} 유저의 추천 내역이 Redis 상에 조회되지 않습니다.")
        exit(1)

if __name__ == "__main__":
    try:
        seed_database()
        run_training_script()
        verify_redis_recommendations()
    except Exception as e:
        print(f"오류: 로컬 파이프라인 검증 도중 에러가 발생했습니다: {e}")
        exit(1)
