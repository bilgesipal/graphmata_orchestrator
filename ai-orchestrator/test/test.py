import asyncio
import websockets
import json
import urllib.parse
import signal
import sys


class WebSocketClient:
    def __init__(self):
        self.uri = "ws://0.0.0.0:8080/ws/ws_query"
        self.Bearer = "xQUAAB%2bLCAAAAAAAAAOFVNuOozgQ%2faId2dBEk8ekuSR0MNvGF%2fDLysZIXExCOnRz%2bfo16YedlXY1jyW76lSdc6qqJa5VVDZpE9%2f0CU9p8%2fNLu9q9XMv10u8XsfxcEv8wX9YDuLj1qCK8Sl6Oitu3DN0UD9tLjm4FOUPUnB%2fnK%2fbK1%2fPu3A05e433P6rln8Klg26Cw7pcPFP2Y%2f0NsHfLJ0jgXdZguTimE9wDMsfexUGPgpuxXPZ14SBTuggoZzSqsQA987K%2bbrCDBuKYt4yxXUbCVFKzZtzLEEd%2bRkQs3WPBOvSWZp6p6PAlgjrTYD%2bkJ9EmnffFTTnLCHmI4Ia59a5o40iDeUxzIyvSrYXbvVQUBu8kTKoumIkfPyQcckSONQ%2fP0MZpCU2uTritiIGclbOKwpz2c6NMPPEePlSEhmcvJlgJH%2bKKmkE7ps7C81QA%2fKW7aSX9UGMoAGc10pydkhy1SWtuBUig7tFYuKJLAHRs%2flEDj6QnndLVTLzTXHN8Uv7R2PhedDoqo7gguWgUtfUMilFnPt%2bvpkna8CECHb0zMypf1MzBDolgqvuYZDmKJRC7AlBoRfYRHaTtB9r%2fjyRiBDEsGXiZCwduMSftUbA1dDM%2bfEkK74VrUNV1gOQD0uGQZ7lJJTlAwqGUdKZZP0scjYCQOKyCPSW5QTik238pu9%2fxEecqGlpFzKaPTIJ5JFfR0PVXffCmz%2fIbfTyb%2f6ICc7ccbfN%2bFEY%2f9LcemAfermB1moRmy49lrgfWxlwyUZB%2bbiUdOhKgt6rHecbNn5J2E7luesJh40%2flh6lgT75HTHAq%2b3ImFLcJmGmxohQDCEhn%2b2CDn%2fhYMNAtJMQhCs0dW7%2fhMHwhTEcqgP6zHp9vItjqQZsfIhaVq63HKur5tt8Or2ax%2foWixyO%2boprBeLL%2bfog%2bWFjLYtnvB87wQ1l9iN0NBgwgAL8qNgyJf7T6MpeEOkxYt%2bAcI2nEw%2fKOEDM72kOEAwrsnK7k%2bDm%2f8n%2fxWwQtnvC%2b9feCTf9Nx40fbf3FN346uhJj57O82v2x9UO7m5Cj6Lmbdp5kJgx%2fJNS7S9ek764eNv6rztyVYzh26lvRA6%2f69ofgofh44jFxklHdbH7I%2bMt06fVR93TF0fxJac0Yq%2b1u45pC9qqu%2bBWvYq1sDnaPNwrogtp4Fp22O1E2l9f%2fvE8vlvtVOeH07xt1gPYQwv%2b5UZ8Fh8ZyZSzmIHpjyu1Ote9u0p6XczM1qo%2f7c3ub0Urn1C8nZI%2bmxTfV6dCkbeCmfgISv4BJi%2fc%2f0mQNduPbeUoEH30Gh%2bAvRcM%2fdsH7Y89SXnvR%2fRx%2fftIrLP4Gytu5QcUFAAA%3d"
        self.running = True

    def create_message(self, user_input, session_id="session_1001", message_id="123"):
        return {
            "headers": {
                "ApplicationId": "99a05e4e-1f0a-4974-a063-b0463f11fd1b",
                "UserId": "prometa@bizigo.com",
                "LanguageCode": "tr",
                "Bearer": self.Bearer
            },
            "payload": {
                "user_input": user_input,
                "session_id": session_id,
                "message_id": message_id,
                "trace_id": 0,
                "sequence": 0
            }
        }

    def signal_handler(self, signum, frame):
        print("\nReceived interrupt signal. Closing connection...")
        self.running = False
        sys.exit(0)

    async def connect_and_listen(self, user_input):
        signal.signal(signal.SIGINT, self.signal_handler)

        message = self.create_message(user_input)

        try:
            print(f"Connecting to {self.uri}")

            extra_headers = {
                "ApplicationId": "99a05e4e-1f0a-4974-a063-b0463f11fd1b",
                "UserId": "prometa@bizigo.com",
                "LanguageCode": "tr",
                "Bearer": self.Bearer
            }

            async with websockets.connect(
                    self.uri,
                    extra_headers=extra_headers,
                    ping_interval=20,  # Keep connection alive
                    ping_timeout=10,
                    close_timeout=10
            ) as websocket:
                print("Connected successfully")
                message_json = json.dumps(message, ensure_ascii=False)
                await websocket.send(message_json)
                print(" Message sent:")
                print(f"  Query: {user_input}")
                print(f"  Session: {message['payload']['session_id']}")
                print(f"  Message ID: {message['payload']['message_id']}")
                print("-" * 50)

                response_count = 0
                try:
                    while self.running:
                        try:
                            response = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=30.0
                            )

                            response_count += 1
                            print(f"\n Response #{response_count}:")

                            try:
                                parsed_response = json.loads(response)

                                if parsed_response.get("status") == "ready":
                                    print(" Server ready - waiting for AI response...")
                                else:
                                    print(json.dumps(parsed_response, indent=2, ensure_ascii=False))

                                    if (parsed_response.get("status") in ["completed", "finished", "done"] or
                                            parsed_response.get("final") == True or
                                            "final" in str(parsed_response).lower()):
                                        print("✓ Response completed")
                                        break

                            except json.JSONDecodeError:
                                print(response)

                        except asyncio.TimeoutError:
                            print(" No response received within timeout period")
                            break

                        except websockets.exceptions.ConnectionClosed:
                            print(" Connection closed by server")
                            break

                except KeyboardInterrupt:
                    print("\n Interrupted by user")

                print(f"\n Total responses received: {response_count}")

        except websockets.exceptions.InvalidStatusCode as e:
            print(f" Connection failed with status code: {e.status_code}")
            print(f"Headers: {e.headers}")
        except websockets.exceptions.WebSocketException as e:
            print(f" WebSocket error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()


async def main():
    client = WebSocketClient()

    query = "Berlinde ote bul!" \

    print(" Starting WebSocket client...")
    print(f"Query: {query}")
    print("Press Ctrl+C to stop\n")

    await client.connect_and_listen(query)


if __name__ == "__main__":
    asyncio.run(main())