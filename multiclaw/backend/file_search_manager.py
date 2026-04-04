"""
Gemini File Search Store integration for MultiClaw.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types


class FileSearchManager:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")

        self.client = genai.Client(api_key=self.api_key)
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.metadata_file = self.data_dir / "file_search_metadata.json"
        self.metadata = self._load_metadata()
        self.store = None
        self.store_name = self.metadata.get("store_name")
        self._initialized = False
        print("Gemini File Search Manager initialized")

    def _load_metadata(self) -> Dict[str, Any]:
        if self.metadata_file.exists():
            try:
                return json.loads(self.metadata_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"store_name": None, "uploaded_files": []}

    def _save_metadata(self) -> None:
        self.metadata_file.write_text(
            json.dumps(self.metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _ensure_store_initialized(self) -> None:
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        existing_store_name = self.metadata.get("store_name")
        if existing_store_name:
            try:
                self.store = await loop.run_in_executor(
                    None,
                    lambda: self.client.file_search_stores.get(name=existing_store_name),
                )
                self.store_name = self.store.name
                self._initialized = True
                return
            except Exception:
                self.store = None
                self.store_name = None

        self.store = await loop.run_in_executor(
            None,
            lambda: self.client.file_search_stores.create(
                config={"display_name": "RAG File Search Store"}
            ),
        )
        self.store_name = self.store.name
        self.metadata["store_name"] = self.store_name
        self._save_metadata()
        self._initialized = True

    async def upload_file(self, file_path: str, display_name: str) -> Dict[str, Any]:
        await self._ensure_store_initialized()
        loop = asyncio.get_event_loop()
        operation = await loop.run_in_executor(
            None,
            lambda: self.client.file_search_stores.upload_to_file_search_store(
                file=file_path,
                file_search_store_name=self.store_name,
                config={"display_name": display_name},
            ),
        )

        while not operation.done:
            await asyncio.sleep(2)
            operation = await loop.run_in_executor(
                None,
                lambda current_operation=operation: self.client.operations.get(current_operation),
            )

        response = operation.response
        file_info = {
            "name": response.document_name,
            "display_name": display_name,
            "uri": response.document_name,
            "mime_type": "application/octet-stream",
            "state": "ACTIVE",
            "upload_time": time.time(),
        }
        self.metadata.setdefault("uploaded_files", []).append(file_info)
        self._save_metadata()
        return {
            "file_name": response.document_name,
            "display_name": display_name,
            "uri": response.document_name,
            "state": "ACTIVE",
        }

    async def get_context(
        self, query: str, max_results: int = 5
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_store_initialized()
        uploaded_files = self.metadata.get("uploaded_files", [])
        if not uploaded_files:
            return None

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Find relevant information for this query: {query}",
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=2000,
                        tools=[
                            types.Tool(
                                file_search=types.FileSearch(
                                    file_search_store_names=[self.store_name]
                                )
                            )
                        ],
                    ),
                ),
            )
            searched_text = response.text if getattr(response, "text", None) else ""
        except Exception:
            searched_text = None

        return {
            "store_name": self.store_name,
            "file_count": len(uploaded_files),
            "files": uploaded_files[-max_results:],
            "searched_context": searched_text,
        }

    def get_uploaded_files(self) -> List[Dict[str, Any]]:
        return self.metadata.get("uploaded_files", [])

    async def list_documents(self) -> Dict[str, Any]:
        documents = self.metadata.get("uploaded_files", [])
        return {
            "success": True,
            "store_name": self.store_name,
            "documents": documents,
            "count": len(documents),
        }

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.files.delete(name=document_id),
            )
        except Exception:
            pass

        uploaded_files = self.metadata.get("uploaded_files", [])
        self.metadata["uploaded_files"] = [
            file_info for file_info in uploaded_files if file_info["name"] != document_id
        ]
        self._save_metadata()
        return {
            "success": True,
            "message": "document deleted",
            "document_id": document_id,
        }

    async def clear_all_documents(self) -> Dict[str, Any]:
        uploaded_files = list(self.metadata.get("uploaded_files", []))
        deleted_count = 0
        loop = asyncio.get_event_loop()

        for file_info in uploaded_files:
            try:
                await loop.run_in_executor(
                    None,
                    lambda name=file_info["name"]: self.client.files.delete(name=name),
                )
                deleted_count += 1
            except Exception:
                continue

        self.metadata["uploaded_files"] = []
        self._save_metadata()
        return {
            "success": True,
            "message": f"{deleted_count} documents deleted",
            "deleted_count": deleted_count,
        }
