from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import TimestampType,IntegerType
from pyspark.sql.functions import year,month
from pyspark.sql.window import Window

input_data_path = "gs://pyspark-fs-sid/stackoverflowposts.csv"

def readData(input_data_path) : 
    
    print("-----Reading Input Data------")

    spark = SparkSession.builder \
    .appName("pyspark-basics") \
    .getOrCreate()

    df = spark.read.csv(input_data_path,header=True)
    return df.select(["tags","view_count","creation_date"])

def dfBasicTransforms():

    print("-----Starting Df Basic Transformations------")

    df_subset = readData(input_data_path)
    df_tagged = df_subset \
        .withColumn(
        'post_type',
        F.when(F.col('tags').like('python%'),'python') \
        .otherwise("others")
    )

    df_tagged = df_tagged \
    .withColumn("creation_date",df_tagged["creation_date"].cast(TimestampType())) \
    .withColumn("view_count",df_tagged["view_count"].cast(IntegerType()))

    df_tagged = df_tagged \
        .withColumn("creation_year",year(df_tagged.creation_date)) \
        .withColumn("creation_month",month(df_tagged.creation_date))

    # ------- Un-Comment the below filter if need be ------- 

    # df_tagged = df_tagged \
    # .filter(
    #     ( df_tagged.creation_year==2015 )
    #     & 
    #     ( df_tagged.post_type=='python')
    # )

    df_tagged = df_tagged.select(["post_type","creation_year","creation_month","view_count"])

    df_tagged = df_tagged.groupBy(["post_type","creation_year","creation_month"]) \
            .agg(
                F.sum("view_count").alias("monthly_views")
            )
    # df_tagged.show(10,False)
    dfAggregations(df_tagged)

def dfAggregations(df):
    print("-----Starting Aggregations------")

    running_sum_window_spec = Window.partitionBy(["post_type","creation_year"]) \
                            .rowsBetween(Window.unboundedPreceding,Window.currentRow) \
                            .orderBy("creation_month")

    df.withColumn("running_total_views",F.sum("monthly_views") \
                     .over(running_sum_window_spec)
                    ).orderBy("creation_month").show(10,False)

    df.write.format('bigquery') \
        .option('table','data_mart.running_agg_output') \
        .option('temporaryGcsBucket','pyspark-fs-sid/tmp_staging') \
        .save()

    print("-----Execution Completed------")


if __name__ == "__main__":
    dfBasicTransforms()
