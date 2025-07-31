from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_custom_post_details():
    # Create a custom post (upload)
    custom_post = {
        "title": "Custom Writeup Title",
        "content": "<h2>Custom Content</h2><p>This is a custom writeup body.</p>",
        "author": "Jane Doe",
        "category": "Custom",
        "published_date": "2025-07-31"
    }
    post_resp = client.post("/custom-post", json=custom_post)
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    url = post_data["url"]
    # Now fetch the details page
    response = client.get(f"/article/{url}")
    assert response.status_code == 200
    html = response.text
    assert "Custom Writeup Title" in html
    assert "Jane Doe" in html
    assert "Custom Content" in html
