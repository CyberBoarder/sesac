import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, when, sum as _sum

## @params: [JOB_NAME, S3_INPUT_PATH, REDSHIFT_TEMP_DIR, REDSHIFT_CONNECTION]
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_INPUT_PATH', 'REDSHIFT_TEMP_DIR', 'REDSHIFT_CONNECTION'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# 1. S3 Landing Zone에서 raw JSON 로그 로드
# 로그 경로 예시: s3://sesac-cosmetic-logs/partition_event_type=*/year=*/month=*/day=*/
s3_input_path = args['S3_INPUT_PATH']
datasource = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [s3_input_path], "recurse": True},
    format="json",
    transformation_ctx="datasource"
)

# PySpark DataFrame으로 변환
df = datasource.toDF()

# 2. 데이터 분석 및 필터링 (Notion 정책 반영)
# - 평점 이벤트(review_rating) 중 평점이 4점 이상인 경우만 학습 반영
# - 평점이 없는 다른 이벤트(product_click, to_cart 등)는 그대로 허용
filtered_df = df.filter(
    (col("event_type") != "review_rating") | 
    ((col("event_type") == "review_rating") & (col("rating") >= 4))
)

# 3. event_type에 따른 고객 상호작용 점수(Interaction Score) 매핑
# - product_click = 1점
# - to_cart = 2점
# - purchase = 3점
# - review_rating (평점 4점 이상) = 5점
# - 기타/로그인 등은 가중치 0 부여
interaction_df = filtered_df.withColumn(
    "weight",
    when(col("event_type") == "product_click", 1)
    .when(col("event_type") == "to_cart", 2)
    .when(col("event_type") == "purchase", 3)
    .when(col("event_type") == "review_rating", 5)
    .otherwise(0)
)

# 가중치가 0보다 큰 유효 인터랙션만 필터링
valid_interaction_df = interaction_df.filter(col("weight") > 0)

# 4. 사용자(user_id)와 상품(product_id) 조합 기준으로 점수 집계 (Aggregation)
aggregated_df = valid_interaction_df.groupBy("user_id", "product_id").agg(
    _sum("weight").alias("interaction_score")
)

# 5. Redshift Data Warehouse로 데이터 적재 (Upsert/OverWrite)
# Redshift 커넥션 설정 로드 및 대상 테이블 쓰기
redshift_connection = args['REDSHIFT_CONNECTION']
redshift_temp_dir = args['REDSHIFT_TEMP_DIR']

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=glueContext.create_dynamic_frame.fromDF(aggregated_df, glueContext, "aggregated_df"),
    catalog_connection=redshift_connection,
    connection_options={
        "dbtable": "public.user_item_interactions",
        "database": "cosmetics_dw"
    },
    redshift_tmp_dir=redshift_temp_dir,
    transformation_ctx="redshift_write"
)

job.commit()
print("Glue ETL Job Successfully Completed.")
