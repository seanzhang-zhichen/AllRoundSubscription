"""
通用Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应模型"""
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")


class DataResponse(BaseResponse, Generic[T]):
    """带数据的响应模型"""
    data: T = Field(description="响应数据")


class PaginatedResponse(BaseResponse, Generic[T]):
    """分页响应模型"""
    data: List[T] = Field(description="数据列表")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页大小")
    total_pages: int = Field(description="总页数")
    
    @classmethod
    def create(cls, data: List[T], total: int, page: int, page_size: int):
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class ErrorResponse(BaseResponse):
    """错误响应模型"""
    code: int = Field(description="错误码")
    message: str = Field(description="错误消息")
    errors: Optional[List[str]] = Field(default=None, description="详细错误信息")


class IDResponse(BaseModel):
    """ID响应模型"""
    id: int = Field(description="资源ID")


class SuccessResponse(BaseModel):
    """成功响应模型"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="操作成功", description="响应消息")