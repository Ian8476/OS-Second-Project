"""Excepciones de dominio + handlers para FastAPI."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.shared.state_machine import InvalidTransition


class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CaseNotFound(DomainError):
    status_code = 404
    code = "case_not_found"


class CaseAlreadyTerminal(DomainError):
    status_code = 409
    code = "case_already_terminal"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.code, "message": exc.message},
        )

    @app.exception_handler(InvalidTransition)
    async def _invalid_transition(_: Request, exc: InvalidTransition):
        return JSONResponse(
            status_code=409,
            content={
                "detail": "invalid_transition",
                "from": exc.from_status,
                "to": exc.to_status,
            },
        )
