import os
import asyncio
import random
import string
import time
from io import BytesIO

import boto3
from PIL import Image


def _compress(data: bytes, max_px: int = 1200) -> bytes:
    img = Image.open(BytesIO(data))
    if img.mode in ('RGBA', 'P', 'LA'):
        img = img.convert('RGB')
    img.thumbnail((max_px, max_px), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format='JPEG', quality=82)
    return out.getvalue()


def _upload_sync(data: bytes, key: str) -> str:
    s3 = boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )
    s3.put_object(
        Bucket=os.getenv('R2_BUCKET_NAME'),
        Key=key,
        Body=data,
        ContentType='image/jpeg'
    )
    return f"{os.getenv('R2_PUBLIC_URL')}/{key}"


async def upload_photo(data: bytes) -> str:
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    key = f"listings/{int(time.time())}-{suffix}.jpg"
    compressed = _compress(data)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upload_sync, compressed, key)
