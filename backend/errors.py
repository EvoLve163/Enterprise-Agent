"""后端统一业务异常。

服务层所有可预期错误都抛出 AppError（携带 HTTP 状态码、机器码、
人类可读信息），由 main.py 的异常处理器统一格式化为：

    {"detail": {"code": "<ERROR_CODE>", "message": "<人类可读信息>"}}
"""

from fastapi import status


class AppError(Exception):
    """业务异常：HTTP 状态码 + 机器码 + 信息。"""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class BadRequestError(AppError):
    def __init__(self, code: str = "BAD_REQUEST", message: str = "请求不合法") -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message)


class NotFoundError(AppError):
    def __init__(self, code: str = "NOT_FOUND", message: str = "资源不存在") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, code, message)


class ConflictError(AppError):
    def __init__(self, code: str = "CONFLICT", message: str = "资源冲突") -> None:
        super().__init__(status.HTTP_409_CONFLICT, code, message)


class UpstreamError(AppError):
    def __init__(self, code: str = "UPSTREAM_ERROR", message: str = "上游服务错误") -> None:
        super().__init__(status.HTTP_502_BAD_GATEWAY, code, message)
