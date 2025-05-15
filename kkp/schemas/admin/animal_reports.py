from pydantic import BaseModel


class EditAnimalReportRequest(BaseModel):
    assigned_to_id: int | None = None
    notes: str | None = None
