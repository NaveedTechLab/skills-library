from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class CreateSchema(BaseSchema):
    """Base for create operations."""

    pass


class UpdateSchema(BaseSchema):
    """Base for update operations - all fields optional."""

    pass


class ResponseSchema(BaseSchema):
    """Base for response models."""

    pass
