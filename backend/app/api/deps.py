from typing import Annotated

from fastapi import Depends, Request

from app.services import Services


class ApiProblem(Exception):
    """An expected API error, rendered as {"detail", "code"}."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]
