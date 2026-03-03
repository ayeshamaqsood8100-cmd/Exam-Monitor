import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.main import app
except Exception as e:
    error_msg = traceback.format_exc().encode('utf-8')
    
    async def app(scope, receive, send):
        assert scope.get('type') == 'http'
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [
                (b'content-type', b'text/plain'),
            ]
        })
        await send({
            'type': 'http.response.body',
            'body': b"FastAPI App Failed to Load. Traceback:\n\n" + error_msg,
        })
