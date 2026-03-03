import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.main import app
except Exception as e:
    # Gather traceback
    error_msg = traceback.format_exc()
    
    # Let's also look at what actually got bundled into vercel!
    try:
        backend_services_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "services")
        bundled_files = "\n".join(os.listdir(backend_services_path))
    except Exception as dir_err:
        bundled_files = f"Could not list directory: {dir_err}"
        
    final_output = f"FastAPI App Failed to Load.\n\nFiles in backend/services:\n{bundled_files}\n\nTraceback:\n{error_msg}".encode('utf-8')
    
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
            'body': final_output,
        })
