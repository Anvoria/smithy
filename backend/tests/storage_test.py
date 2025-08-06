from app.core.storage import get_storage_provider
import asyncio

storage = get_storage_provider()
print(f"Using storage: {storage}")


async def test_storage_operations():
    metadata = await storage.upload(
        file=b"test content", filename="test.txt", content_type="text/plain"
    )
    print(f"Uploaded: {metadata.public_url}")


if __name__ == "__main__":
    asyncio.run(test_storage_operations())
    print("Storage test completed.")
