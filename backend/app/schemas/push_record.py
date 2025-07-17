"""
推送记录相关Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.push_record import PushStatus


class PushRecordBase(BaseModel):
    """推送记录基础模型"""
    user_id: int = Field(..., description="用户ID")
    article_id: int = Field(..., description="文章ID")
    push_time: datetime = Field(..., description="推送时间")
    status: str = Field(..., description="推送状态")
    error_message: Optional[str] = Field(None, max_length=500, description="错误信息")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [status.value for status in PushStatus]
        if v not in valid_statuses:
            raise ValueError(f'不支持的推送状态: {v}，支持的状态: {valid_statuses}')
        return v


class PushRecordCreate(PushRecordBase):
    """推送记录创建模型"""
    pass


class PushRecordUpdate(BaseModel):
    """推送记录更新模型"""
    status: Optional[str] = Field(None, description="推送状态")
    error_message: Optional[str] = Field(None, max_length=500, description="错误信息")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [status.value for status in PushStatus]
            if v not in valid_statuses:
                raise ValueError(f'不支持的推送状态: {v}，支持的状态: {valid_statuses}')
        return v


class PushRecordResponse(PushRecordBase):
    """推送记录响应模型"""
    id: int = Field(description="推送记录ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    is_success: bool = Field(description="是否推送成功")
    is_failed: bool = Field(description="是否推送失败")
    
    class Config:
        from_attributes = True


class PushRecordWithDetails(PushRecordResponse):
    """带详细信息的推送记录模型"""
    user_nickname: Optional[str] = Field(None, description="用户昵称")
    article_title: str = Field(description="文章标题")
    article_url: str = Field(description="文章链接")
    account_name: str = Field(description="账号名称")
    account_platform: str = Field(description="账号平台")
    platform_display_name: str = Field(description="平台显示名称")


class PushRecordList(BaseModel):
    """推送记录列表查询模型"""
    user_id: Optional[int] = Field(None, description="用户ID筛选")
    status: Optional[str] = Field(None, description="状态筛选")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")
    order_by: str = Field(default="push_time", description="排序字段")
    order_desc: bool = Field(default=True, description="是否降序")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [status.value for status in PushStatus]
            if v not in valid_statuses:
                raise ValueError(f'不支持的推送状态: {v}')
        return v
    
    @validator('order_by')
    def validate_order_by(cls, v):
        allowed_fields = ['push_time', 'created_at', 'status']
        if v not in allowed_fields:
            raise ValueError(f'不支持的排序字段: {v}，支持的字段: {allowed_fields}')
        return v


class PushStats(BaseModel):
    """推送统计模型"""
    total_pushes: int = Field(description="总推送数")
    success_pushes: int = Field(description="成功推送数")
    failed_pushes: int = Field(description="失败推送数")
    pending_pushes: int = Field(description="待推送数")
    success_rate: float = Field(description="成功率")
    today_pushes: int = Field(description="今日推送数")
    daily_limit: int = Field(description="每日推送限制")
    remaining_pushes: int = Field(description="今日剩余推送数")


class BatchPushCreate(BaseModel):
    """批量推送创建模型"""
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    article_id: int = Field(..., description="文章ID")
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('用户ID列表中存在重复项')
        return v


class BatchPushResponse(BaseModel):
    """批量推送响应模型"""
    total_users: int = Field(description="总用户数")
    success_count: int = Field(description="成功推送数量")
    failed_count: int = Field(description="失败推送数量")
    skipped_count: int = Field(description="跳过推送数量")
    push_records: List[PushRecordResponse] = Field(description="推送记录列表")