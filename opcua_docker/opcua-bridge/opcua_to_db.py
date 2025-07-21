"""
OPC UA → MySQL Bridge
---------------------
* InspectSystem/ 트리거 플래그가 `True` 로 바뀌면
  - Angle · Vision1 · Vision2 · Voltage 값을 읽어 DB 반영  
* lot_db_helper 가 제공하는 헬퍼 함수를 사용하므로
  커넥션 / 커밋 처리는 헬퍼 내부에서 자동으로 완료됨
"""

from __future__ import annotations

import asyncio, os
from typing import Optional

from asyncua import Client
from dotenv import load_dotenv

from lot_db_helper import (
    insert_vision1,
    update_vision2,
    update_voltage,
)

# 1. 환경 변수
# ──────────────────────────────────────────────────────────────────────────
load_dotenv("config.env")

UA_ENDPOINT   = os.getenv("UA_ENDPOINT", "opc.tcp://localhost:4840/inspect/server/")
MODULE_TYPE   = os.getenv("MODULE_TYPE", "2x3")   # Vision1 측정 모듈 타입 기본값

# 2. UA → DB Bridge
# ──────────────────────────────────────────────────────────────────────────
INSPECT_PATH = "ns=2;s=InspectSystem/"
NODE_KEYS = [
    "TriggerFlag",
    "Angle",
    "Vision1Result",
    "Vision2Result",
    "Voltage",
    "VoltageResult",
]


async def process_once(nodes: dict[str, "Node"]) -> None:
    """
    TriggerFlag 가 True 로 바뀐 순간 한 번 값을 읽어 DB 반영
    """
    angle: float              = await nodes["Angle"].read_value()
    v1_result: str            = await nodes["Vision1Result"].read_value()
    v2_result: str            = await nodes["Vision2Result"].read_value()
    volt: float               = await nodes["Voltage"].read_value()
    volt_result: str          = await nodes["VoltageResult"].read_value()

    lot: Optional[str] = None

    # Vision1 ⇒ LOT 신규 발급 및 INSERT
    if v1_result:
        lot = insert_vision1(MODULE_TYPE, angle, v1_result)

    # Vision2 / Voltage ⇒ LOT 존재할 때 UPDATE
    if v2_result and lot:
        update_vision2(lot, v2_result)

    if volt and lot:
        # VoltageResult 값이 없으면 OK/NG 판단을 대신할 수도 있다.
        volt_result = volt_result or "NG"
        update_voltage(lot, volt, volt_result)


async def main() -> None:
    async with Client(UA_ENDPOINT) as cli:
        # 노드 바인딩
        nodes = {k: cli.get_node(INSPECT_PATH + k) for k in NODE_KEYS}

        prev_trg = False
        while True:
            trg: bool = await nodes["TriggerFlag"].read_value()

            # Falling → Rising edge 감지
            if not prev_trg and trg:
                try:
                    await process_once(nodes)
                finally:
                    # 트리거 리셋 (에러 발생해도 False 로 돌려놓음)
                    await nodes["TriggerFlag"].write_value(False)

            prev_trg = trg
            await asyncio.sleep(0.1)
            
# 3. Entrypoint
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("중단되었습니다.")