import os
import boto3

bucket = os.environ.get("S3_BUCKET")
s3 = boto3.client("s3")
prefix = "documentos/"

try:
    #s3_obj = s3.get_object(Bucket=bucket, Key=prefix)

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)

    #xml_content = s3_obj["Body"].read().decode("utf-8", errors="ignore")

    #len(xml_content)  # Ensure xml_content is not empty
    print(f"[DEBUG] XML content length: {len(response)}")
    
    lstXml = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".xml")]
    
    print(f"[DEBUG] XML content length: {len(lstXml)}")



except Exception as e:
    print(f"[ERRO] Falha ao processar arquivo {prefix}: {e}")
    raise