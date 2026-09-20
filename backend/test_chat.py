from dotenv import load_dotenv
load_dotenv()
import asyncio
from app.routers.chat import chat_with_agent, ChatRequest
from app.models.user import User

async def main():
    u = User(id=1, name="TestUser")
    r = ChatRequest(prompt="Suggest me an action movie")
    print("Testing chat_with_agent...")
    try:
        res = await chat_with_agent(r, u)
        print("SUCCESS:")
        print(res)
    except Exception as e:
        print("FAILED:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
