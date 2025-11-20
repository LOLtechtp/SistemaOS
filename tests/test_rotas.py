def test_login_page(client):
    resp = client.get('/login')
    assert resp.status_code == 200

def test_home_requires_login(client):
    resp = client.get('/')
    assert resp.status_code in (301, 302)
