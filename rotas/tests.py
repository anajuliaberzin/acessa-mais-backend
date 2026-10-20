import copy
import io
import json
from http.client import IncompleteRead
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from .services.routing_service import MAX_RESPONSE_BYTES, ORS_URL


ENTRADA = {
    "origem": {"latitude": -23.5015, "longitude": -47.4526},
    "destino": {"latitude": -23.5100, "longitude": -47.4600},
}


def feature(duracao=720, distancia=950, extras=None):
    return {
        "type": "Feature",
        "properties": {"summary": {"duration": duracao, "distance": distancia}, "extras": extras or {}},
        "geometry": {"type": "LineString", "coordinates": [[-47.4526, -23.5015], [-47.46, -23.51]]},
    }


@override_settings(ROUTING_API_KEY="test-key", ROUTING_TIMEOUT_SECONDS="10")
class CompararRotasTests(SimpleTestCase):
    """POST real pela stack DRF; somente o transporte externo é mockado. Sem banco."""

    def setUp(self):
        self.client = APIClient()
        patcher = patch("rotas.services.routing_service.build_opener")
        self.opener = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self.response = self.opener.open.return_value.__enter__.return_value
        self.respond(feature())

    def respond(self, *features):
        self.response.read.return_value = json.dumps({"type": "FeatureCollection", "features": features}).encode()

    def post(self, data=None):
        return self.client.post("/api/rotas/comparar/", ENTRADA if data is None else data, format="json")

    def test_valid_public_request_and_provider_contract(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, ORS_URL)
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "test-key")
        self.assertEqual(self.opener.open.call_args.kwargs, {"timeout": 10.0})
        body = json.loads(request.data)
        self.assertEqual(body["coordinates"], [[-47.4526, -23.5015], [-47.46, -23.51]])
        self.assertEqual(body["preference"], "fastest")
        self.assertEqual(body["alternative_routes"]["target_count"], 3)
        self.assertEqual(body["extra_info"], ["waytype", "surface", "steepness"])
        self.assertFalse(body["instructions"])

    def test_output_normalized_and_no_provider_metadata_leaked(self):
        payload = feature()
        payload["properties"]["private_metadata"] = "test-key"
        self.respond(payload)
        response = self.post()
        route = response.data["rota_rapida"]
        self.assertEqual(route["tempo_minutos"], 12)
        self.assertEqual(route["distancia_metros"], 950)
        self.assertEqual(route["geometria"], payload["geometry"])
        self.assertNotIn("test-key", response.content.decode())
        self.assertNotIn("summary", route)

    def test_fastest_is_minimum_duration_not_order_or_distance(self):
        self.respond(feature(1020, 800), feature(720, 950), feature(900, 850))
        response = self.post()
        self.assertEqual(response.data["rota_rapida"]["distancia_metros"], 950)
        self.assertEqual(len(response.data["alternativas"]), 2)

    def test_selection_before_rounding_and_distance_tiebreaker(self):
        self.respond(feature(720.02, 800), feature(720.01, 950), feature(720.01, 900))
        self.assertEqual(self.post().data["rota_rapida"]["distancia_metros"], 900)

    def test_missing_origin(self):
        response = self.post({"destino": ENTRADA["destino"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("origem", response.data)
        self.opener.open.assert_not_called()

    def test_missing_destination(self):
        response = self.post({"origem": ENTRADA["origem"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("destino", response.data)
        self.opener.open.assert_not_called()

    def test_invalid_coordinates_and_missing_fields(self):
        for field, values in {
            "latitude": [91, -91, None, True, "endereço", "-23.5", [], {}, 10 ** 400],
            "longitude": [181, -181, None, False, "-47.4", [], {}],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = copy.deepcopy(ENTRADA)
                    data["origem"][field] = value
                    self.assertEqual(self.post(data).status_code, 400)
            data = copy.deepcopy(ENTRADA)
            del data["destino"][field]
            self.assertEqual(self.post(data).status_code, 400)
        self.opener.open.assert_not_called()

    def test_coordinate_boundaries_are_valid(self):
        response = self.post({"origem": {"latitude": -90, "longitude": -180},
                              "destino": {"latitude": 90, "longitude": 180}})
        self.assertEqual(response.status_code, 200)

    def test_invalid_nested_and_root_structures(self):
        for value in [None, [], "Praça", 42, True]:
            for field in ("origem", "destino"):
                with self.subTest(value=value, field=field):
                    data = copy.deepcopy(ENTRADA)
                    data[field] = value
                    self.assertEqual(self.post(data).status_code, 400)
        for data in [[], "endereço", 42]:
            self.assertEqual(self.post(data).status_code, 400)
        self.opener.open.assert_not_called()

    def test_invalid_json_and_nonfinite_coordinates(self):
        for content in ['{', '{"origem":{"latitude":NaN}}', '{"origem":{"latitude":Infinity}}']:
            self.assertEqual(self.client.post("/api/rotas/comparar/", content, content_type="application/json").status_code, 400)
        self.opener.open.assert_not_called()

    def test_empty_feature_collection(self):
        self.respond()
        response = self.post()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["codigo"], "rota_nao_encontrada")

    def test_provider_route_and_point_not_found(self):
        for code in (2009, 2010):
            self.opener.open.side_effect = HTTPError(ORS_URL, 404, "secret", {}, io.BytesIO(json.dumps({"error": {"code": code}}).encode()))
            self.assertEqual(self.post().status_code, 404)

    def test_provider_failure_statuses_and_no_sensitive_details(self):
        for status, expected in [(400, 502), (401, 503), (403, 503), (404, 502), (429, 503),
                                 (500, 503), (503, 503), (504, 504), (302, 502)]:
            with self.subTest(status=status):
                self.opener.open.side_effect = HTTPError(ORS_URL, status, "test-key", {}, io.BytesIO(b"test-key"))
                response = self.post()
                self.assertEqual(response.status_code, expected)
                self.assertNotIn("test-key", response.content.decode())
                self.assertNotIn(ORS_URL, response.content.decode())

    def test_timeout(self):
        for error in [TimeoutError("test-key"), URLError(TimeoutError("secret"))]:
            self.opener.open.side_effect = error
            response = self.post()
            self.assertEqual(response.status_code, 504)
            self.assertEqual(response.data["codigo"], "tempo_esgotado")

    def test_unavailable_network(self):
        self.opener.open.side_effect = URLError("test-key")
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("test-key", response.content.decode())

    def test_truncated_http_response(self):
        self.response.read.side_effect = IncompleteRead(b"partial")
        self.assertEqual(self.post().status_code, 502)

    def test_truncated_provider_error_does_not_leak_or_raise_500(self):
        error = HTTPError(ORS_URL, 503, "test-key", {}, io.BytesIO())
        self.opener.open.side_effect = error
        with patch.object(error, "read", side_effect=IncompleteRead(b"test-key")):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("test-key", response.content.decode())

    @override_settings(ROUTING_API_KEY=" ")
    def test_missing_key(self):
        self.assertEqual(self.post().status_code, 503)
        self.opener.open.assert_not_called()

    def test_invalid_timeout_configuration(self):
        for timeout in ("oops", "nan", "inf", "0", "-1", "61"):
            with self.settings(ROUTING_TIMEOUT_SECONDS=timeout):
                self.assertEqual(self.post().status_code, 503)
        self.opener.open.assert_not_called()

    def test_invalid_json_or_oversized_provider_response(self):
        for content in [b"not json", b"\xff", b"x" * (MAX_RESPONSE_BYTES + 1)]:
            self.response.read.return_value = content
            self.assertEqual(self.post().status_code, 502)

    def test_invalid_provider_structure(self):
        for payload in [None, [], {}, {"type": "FeatureCollection"},
                        {"type": "FeatureCollection", "features": [None]},
                        {"type": "FeatureCollection", "features": [{}]}]:
            self.response.read.return_value = json.dumps(payload).encode()
            self.assertEqual(self.post().status_code, 502)

    def test_invalid_geometry_and_summary(self):
        variants = []
        for geometry in [None, {}, {"type": "Point", "coordinates": [0, 0]},
                         {"type": "LineString", "coordinates": [[0, 0]]},
                         {"type": "LineString", "coordinates": [[181, 0], [0, 0]]},
                         {"type": "LineString", "coordinates": [[False, 0], [0, 0]]}]:
            data = feature()
            data["geometry"] = geometry
            variants.append(data)
        for value in [-1, None, "720", True, float("nan"), float("inf"), 10 ** 400]:
            data = feature(duracao=value)
            variants.append(data)
        for data in variants:
            self.respond(data)
            self.assertEqual(self.post().status_code, 502)

    def test_no_accessibility_data_never_fabricates_score_or_candidate(self):
        self.respond(feature(), feature(1020, 1200))
        response = self.post()
        self.assertIsNone(response.data["rota_acessivel"])
        self.assertFalse(response.data["acessibilidade_avaliada"])
        self.assertEqual(response.data["nivel_confianca"], "limitado")
        self.assertIsNone(response.data["rota_rapida"]["score_acessibilidade"])
        self.assertEqual(response.data["rota_rapida"]["barreiras"], [])

    def test_only_real_attributes_produce_barrier_descriptions(self):
        self.respond(feature(extras={"waytype": {"values": [[0, 1, 8]]},
                                     "surface": {"values": [[0, 1, 15]]},
                                     "steepness": {"values": [[0, 1, -3]]}}))
        response = self.post()
        barriers = response.data["rota_rapida"]["barreiras"]
        self.assertEqual([x["tipo"] for x in barriers], ["escada", "superficie", "inclinacao"])
        self.assertEqual(barriers[0]["trecho"], [0, 1])
        self.assertIn("areia", barriers[1]["descricao"])
        self.assertIn("Descida", barriers[2]["descricao"])
        self.assertIsNone(response.data["rota_acessivel"])
        self.assertFalse(response.data["acessibilidade_avaliada"])

    def test_unknown_or_malformed_attributes_do_not_imply_accessibility(self):
        for extras in [None, [], {"waytype": None}, {"surface": {"values": "bad"}},
                       {"waytype": {"values": [[0, 1, 0], [0, 1, 999], [0, 9, 8], [0, 1, True], [0, 1], None]}}]:
            data = feature()
            data["properties"]["extras"] = extras
            self.respond(data)
            response = self.post()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["rota_rapida"]["barreiras"], [])
            self.assertIsNone(response.data["rota_acessivel"])

    def test_single_route_not_duplicated(self):
        response = self.post()
        self.assertEqual(response.data["alternativas"], [])
        self.assertIsNone(response.data["rota_acessivel"])

    def test_public_even_with_expired_token_and_method_restriction(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired")
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.client.get("/api/rotas/comparar/").status_code, 405)
