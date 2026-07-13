import os

from celery import Celery

celery_app = Celery(
    "documents",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)
celery_app.conf.task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "true").lower() in {"1", "true", "yes"}
celery_app.conf.task_eager_propagates = True


@celery_app.task(name="documents.process")
def process_document(document_id: str, checksum: str, storage_path: str) -> dict[str, str]:
    return {"document_id": document_id, "checksum": checksum, "storage_path": storage_path}


def submit_document_processing(document_id: str, checksum: str, storage_path: str) -> None:
    process_document.delay(document_id, checksum, storage_path)
