"""
OPC UA → MySQL Bridge
---------------------
InspectSystem/TriggerFlag 가 True 로 바뀌면
  - Angle · Vision1Result · Vision2Result · Voltage · VoltageResult 값을 읽어
    lot_db_helper 헬퍼 함수로 DB 반영
"""

import asyncio
import os

from asyncua import Client
from dotenv import load_dotenv

from lot_db_helper import (
    insert_vision1,
    update_vision2,
    update_voltage,
)

# 1) 환경 변수 로드
load_dotenv("config.env")
UA_ENDPOINT  = os.getenv("UA_ENDPOINT",  "opc.tcp://opcua-server:4840/inspect/server/")
UA_NAMESPACE = os.getenv("UA_NAMESPACE", "http://inspect.system")
MODULE_TYPE  = os.getenv("MODULE_TYPE",  "2x3")

# 2) 다룰 노드 이름 목록
NODE_KEYS = [
    "TriggerFlag",
    "Angle",
    "Vision1Result",
    "Vision2Result",
    "Voltage",
    "VoltageResult",
]


async def process_once(nodes: dict[str, "Node"]) -> None:
    """TriggerFlag=True 된 순간 한 번만 값을 읽어서 DB에 반영"""
    angle    = await nodes["Angle"].read_value()
    v1       = await nodes["Vision1Result"].read_value()
    v2       = await nodes["Vision2Result"].read_value()
    volt     = await nodes["Voltage"].read_value()
    volt_res = await nodes["VoltageResult"].read_value()

    lot: str | None = None
    if v1:
        lot = insert_vision1(MODULE_TYPE, angle, v1)
    if lot and v2:
        update_vision2(lot, v2)
    if lot and (volt is not None):
        update_voltage(lot, volt, volt_res or "NG")


async def run_bridge() -> None:
    """OPC UA 서버에 연결하고, TriggerFlag 감시 → DB 반영"""
    while True:
        try:
            async with Client(UA_ENDPOINT) as cli:
                # (1) 네임스페이스 인덱스 얻기
                idx = await cli.get_namespace_index(UA_NAMESPACE)
                print(f"▶ namespace index for {UA_NAMESPACE} = {idx}")

                # (2) InspectSystem 객체 Node 바인딩
                # 직접 get_node 로 NodeId("ns=idx;s=InspectSystem") 취득
                inspect_nid = f"ns={idx};s=InspectSystem"
                print(f"▶ bound InspectSystem -> {inspect_nid}")

                # (3) 각 변수 NodeId로 바로 바인딩
                nodes: dict[str, "Node"] = {}
                for key in NODE_KEYS:
                    nid = f"ns={idx};s={key}"
                    nodes[key] = cli.get_node(nid)
                    print(f"   • bound {key} -> {nid}")

                print("✅ OPC UA Bridge 연결 완료, 트리거 대기 시작")

                prev_trg = False
                # (4) TriggerFlag 감시 루프
                while True:
                    try:
                        trg = await nodes["TriggerFlag"].read_value()
                    except Exception as e:
                        print("⚠️ TriggerFlag 읽기 오류:", e)
                        break  # 연결 재설정
                    if not prev_trg and trg:
                        try:
                            await process_once(nodes)
                        finally:
                            # 처리 후 반드시 플래그 리셋
                            await nodes["TriggerFlag"].write_value(False)
                    prev_trg = trg
                    await asyncio.sleep(0.1)

        except (OSError, asyncio.TimeoutError) as e:
            print("⚠️ OPC UA Bridge 연결 실패:", e, "→ 5초 후 재시도")
        except Exception as e:
            print("❌ Bridge 내부 예외:", e, "→ 5초 후 재시도")
        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(run_bridge())
    except KeyboardInterrupt:
        print("중단되었습니다.")