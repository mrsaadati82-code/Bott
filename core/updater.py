# ============================================================
# core/updater.py - Bale API client + getUpdates poller
# ============================================================
# This is the ONLY place that speaks HTTP to https://tapi.bale.ai.
# All bot tokens flow through here. Other modules use BaleAPI
# instances via core.bot_manager.
#
# Reference: https://docs.bale.ai
# ============================================================

import json
import time
from typing import Any, Dict, List, Optional

import requests

from config import (
    bale_api_url,
    POLL_TIMEOUT,
    POLL_LIMIT,
    POLL_ERROR_SLEEP,
)
from monitoring.logs import get_logger

log = get_logger(__name__)


class BaleAPIError(Exception):
    def __init__(self, error_code: int, description: str):
        super().__init__("Bale API error {}: {}".format(error_code, description))
        self.error_code = error_code
        self.description = description


class BaleAPI:
    """
    Thin HTTP client around the Bale Bot API.
    One instance per bot token.
    """

    def __init__(self, token: str):
        self.token = token
        self._session = requests.Session()

    # ------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------
    def call(self, method: str, params: Optional[Dict[str, Any]] = None,
             files: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Any:
        url = bale_api_url(self.token, method)
        try:
            if files:
                resp = self._session.post(url, data=params or {}, files=files, timeout=timeout)
            else:
                resp = self._session.post(url, json=params or {}, timeout=timeout)
        except requests.RequestException as e:
            log.warning("HTTP error calling %s: %s", method, e)
            raise

        try:
            data = resp.json()
        except ValueError:
            raise BaleAPIError(-1, "Invalid JSON response: {}".format(resp.text[:200]))

        if not data.get("ok"):
            raise BaleAPIError(
                int(data.get("error_code", -1)),
                str(data.get("description", "")),
            )
        return data.get("result")

    # ------------------------------------------------------------
    # Common API methods (we add only what's used by the core).
    # Other modules can call self.call('anyMethod', {...}) freely.
    # ------------------------------------------------------------
    def get_me(self) -> Dict[str, Any]:
        return self.call("getMe", timeout=15)

    def get_updates(self, offset: int = 0, limit: int = POLL_LIMIT,
                    timeout: int = POLL_TIMEOUT) -> List[Dict[str, Any]]:
        # HTTP timeout slightly larger than long-poll timeout.
        return self.call(
            "getUpdates",
            {"offset": offset, "limit": limit, "timeout": timeout},
            timeout=timeout + 10,
        ) or []

    def send_message(self, chat_id, text: str,
                     reply_markup: Optional[dict] = None,
                     reply_to_message_id: Optional[int] = None,
                     parse_mode: Optional[str] = None) -> Dict[str, Any]:
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        return self.call("sendMessage", payload)

    def edit_message_text(self, chat_id, message_id: int, text: str,
                          reply_markup: Optional[dict] = None,
                          parse_mode: Optional[str] = None) -> Dict[str, Any]:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if parse_mode is not None:
            payload["parse_mode"] = parse_mode
        return self.call("editMessageText", payload)

    def answer_callback_query(self, callback_query_id: str,
                              text: Optional[str] = None,
                              show_alert: bool = False) -> Dict[str, Any]:
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        return self.call("answerCallbackQuery", payload)

    def delete_message(self, chat_id, message_id: int) -> Dict[str, Any]:
        return self.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


# ============================================================
# Poller: drives getUpdates for one bot in its own loop.
# Owned by core.bot_manager (one Poller per bot).
# ============================================================

class Poller:
    """
    Repeatedly calls getUpdates and forwards updates to a handler.
    Tracks last update id per bot in the DB (bots.last_update_id)
    so we never lose or duplicate updates across restarts.
    """

    def __init__(self, api: BaleAPI, bot_id: int, initial_offset: int,
                 on_update):
        self.api = api
        self.bot_id = bot_id
        self.offset = int(initial_offset or 0)
        self.on_update = on_update  # callable(bot_id, update_dict)
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        log.info("Poller started for bot_id=%s offset=%s", self.bot_id, self.offset)
        while self._running:
            try:
                updates = self.api.get_updates(
                    offset=self.offset + 1 if self.offset else 0,
                    limit=POLL_LIMIT,
                    timeout=POLL_TIMEOUT,
                )
                for upd in updates:
                    try:
                        self.on_update(self.bot_id, upd)
                    except Exception as e:
                        log.exception("Handler error on bot %s: %s", self.bot_id, e)
                    finally:
                        uid = int(upd.get("update_id", 0))
                        if uid > self.offset:
                            self.offset = uid
                            # Persist progress so we resume after restart.
                            try:
                                from database.db import db
                                db.execute(
                                    "UPDATE bots SET last_update_id=? WHERE id=?",
                                    (self.offset, self.bot_id),
                                )
                            except Exception:
                                pass
            except BaleAPIError as e:
                log.error("Bale API error on bot %s: %s", self.bot_id, e)
                time.sleep(POLL_ERROR_SLEEP)
            except requests.RequestException as e:
                log.warning("Network error on bot %s: %s", self.bot_id, e)
                time.sleep(POLL_ERROR_SLEEP)
            except Exception as e:
                log.exception("Unexpected poller error on bot %s: %s", self.bot_id, e)
                time.sleep(POLL_ERROR_SLEEP)
        log.info("Poller stopped for bot_id=%s", self.bot_id)
