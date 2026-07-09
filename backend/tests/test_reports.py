def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_download_report(client):
    payload = {
        "name": "Q1 Report",
        "rows": [
            {"account": "Revenue", "period": "2026-Q1", "amount": 1000.0},
            {"account": "COGS", "period": "2026-Q1", "amount": -400.0},
        ],
    }
    resp = client.post("/api/v1/reports", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "completed"
    report_id = data["id"]

    # Download the generated file
    dl = client.get(f"/api/v1/reports/{report_id}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )


def test_get_missing_report_returns_404(client):
    resp = client.get("/api/v1/reports/999")
    assert resp.status_code == 404
