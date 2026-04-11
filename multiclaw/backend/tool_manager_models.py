from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ToolTransport = Literal["stdio", "http"]
ToolCapability = Literal["reference", "diagram", "repo", "cloud", "validation"]
ToolUsageScope = Literal["prompt", "generate", "diagram", "review", "manage"]


class ToolEnvEntry(BaseModel):
    key: str
    value: str


class ToolRegistrationRequest(BaseModel):
    name: str = Field(min_length=1)
    github_url: str = ""
    description: str = ""
    transport: ToolTransport = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: list[ToolEnvEntry] = Field(default_factory=list)
    url: str = ""
    capabilities: list[ToolCapability] = Field(default_factory=list)
    usage_scopes: list[ToolUsageScope] = Field(default_factory=list)
    raw_json: str = ""


class ToolCheckRequest(BaseModel):
    name: str = ""
    github_url: str = ""
    transport: ToolTransport = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: list[ToolEnvEntry] = Field(default_factory=list)
    url: str = ""
    capabilities: list[ToolCapability] = Field(default_factory=list)
    usage_scopes: list[ToolUsageScope] = Field(default_factory=list)
    raw_json: str = ""


class ToolConfigEntry(BaseModel):
    name: str
    github_url: str = ""
    description: str = ""
    transport: ToolTransport = "stdio"
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    capabilities: list[ToolCapability] = Field(default_factory=list)
    usage_scopes: list[ToolUsageScope] = Field(default_factory=list)
    source: Literal["form", "json"] = "form"


class ToolCheckResponse(BaseModel):
    valid: bool
    summary: str
    checks: list[str] = Field(default_factory=list)
    normalized_entry: ToolConfigEntry | None = None


class ToolManagerConfigResponse(BaseModel):
    config_path: str
    entries: list[ToolConfigEntry] = Field(default_factory=list)
    raw_json: str = ""


class ToolDeleteResponse(BaseModel):
    deleted: bool
    name: str
    message: str


class MCPToolCallResult(BaseModel):
    server_name: str
    tool_name: str
    success: bool
    content: str = ""
    raw_payload: dict[str, object] = Field(default_factory=dict)
    message: str = ""


class MCPToolListResponse(BaseModel):
    server_name: str
    tools: list[dict] = Field(default_factory=list)
    success: bool
    message: str = ""


class MCPCallRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)
