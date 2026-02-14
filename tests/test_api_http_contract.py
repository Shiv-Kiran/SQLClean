import unittest


class TestApiHttpContract(unittest.TestCase):
    @unittest.skipUnless(
        __import__("importlib").util.find_spec("fastapi") is not None
        and __import__("importlib").util.find_spec("starlette") is not None,
        "fastapi/starlette not installed",
    )
    def test_http_optimize_endpoint(self):
        from starlette.testclient import TestClient

        from api.fastapi_app import SQLCleanAPI, create_fastapi_app
        from api.grpc_server import SQLCleanGrpcService

        api_service = SQLCleanAPI.create(
            processor=lambda payload: {
                "optimized_sql": "SELECT 123",
                "meta": {"echo": payload.get("sql_input", "")},
            },
            start_worker=False,
        )
        app = create_fastapi_app(api_service=api_service)
        grpc = SQLCleanGrpcService(api_service=api_service)

        with TestClient(app) as client:
            resp = client.post("/v1/optimize", json={"sql_input": "SELECT * FROM users"})
            self.assertEqual(resp.status_code, 200)
            http_payload = resp.json()

        grpc_payload = grpc.Optimize({"sql_input": "SELECT * FROM users"})
        self.assertEqual(http_payload["optimized_sql"], grpc_payload["optimized_sql"])


if __name__ == "__main__":
    unittest.main()

