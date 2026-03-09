from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.core.errors import BadGatewayError
from app.modules.ad_factory import kling_client


class SubmitTextToVideoTests(unittest.TestCase):
    @patch("app.modules.ad_factory.kling_client.requests.post")
    @patch("app.modules.ad_factory.kling_client._get_auth_header", return_value="Bearer token")
    @patch(
        "app.modules.ad_factory.kling_client._get_config",
        return_value=("https://api-singapore.klingai.com", "ak", "sk"),
    )
    def test_submit_text_to_video_uses_v26_payload(
        self,
        _mock_config: Mock,
        _mock_auth: Mock,
        mock_post: Mock,
    ) -> None:
        response = Mock()
        response.ok = True
        response.json.return_value = {"data": {"task_id": "task-123"}}
        mock_post.return_value = response

        task_id = kling_client.submit_text_to_video(
            prompt="  portrait launch video  ",
            duration=10,
            aspect_ratio="9:16",
        )

        self.assertEqual(task_id, "task-123")
        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["json"],
            {
                "model_name": kling_client.KLING_TEXT_TO_VIDEO_MODEL,
                "mode": kling_client.KLING_TEXT_TO_VIDEO_MODE,
                "prompt": "portrait launch video",
                "duration": "10",
                "aspect_ratio": "9:16",
                "sound": "off",
            },
        )

    @patch("app.modules.ad_factory.kling_client.requests.post")
    @patch("app.modules.ad_factory.kling_client._get_auth_header", return_value="Bearer token")
    @patch(
        "app.modules.ad_factory.kling_client._get_config",
        return_value=("https://api-singapore.klingai.com", "ak", "sk"),
    )
    def test_submit_text_to_video_wraps_provider_bad_request(
        self,
        _mock_config: Mock,
        _mock_auth: Mock,
        mock_post: Mock,
    ) -> None:
        response = Mock()
        response.ok = False
        response.status_code = 400
        response.json.return_value = {"message": "duration is invalid"}
        response.text = '{"message":"duration is invalid"}'
        mock_post.return_value = response

        with self.assertRaises(BadGatewayError) as ctx:
            kling_client.submit_text_to_video(
                prompt="portrait launch video",
                duration=10,
                aspect_ratio="9:16",
            )

        self.assertIn("Kling rejected the render request", ctx.exception.message)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.data["provider_status"], 400)
        self.assertEqual(ctx.exception.data["provider"], "kling")


class GetTaskStatusTests(unittest.TestCase):
    @patch("app.modules.ad_factory.kling_client.requests.get")
    @patch("app.modules.ad_factory.kling_client._get_auth_header", return_value="Bearer token")
    @patch(
        "app.modules.ad_factory.kling_client._get_config",
        return_value=("https://api-singapore.klingai.com", "ak", "sk"),
    )
    def test_get_task_status_falls_back_to_legacy_endpoint(
        self,
        _mock_config: Mock,
        _mock_auth: Mock,
        mock_get: Mock,
    ) -> None:
        first_response = Mock()
        first_response.status_code = 404
        first_response.ok = False

        second_response = Mock()
        second_response.status_code = 200
        second_response.ok = True
        second_response.json.return_value = {"data": {"task_status": "succeed"}}

        mock_get.side_effect = [first_response, second_response]

        payload = kling_client.get_task_status("task-123")

        self.assertEqual(payload, {"data": {"task_status": "succeed"}})
        first_call = mock_get.call_args_list[0]
        second_call = mock_get.call_args_list[1]
        self.assertEqual(
            first_call.args[0],
            "https://api-singapore.klingai.com/v1/videos/text2video/task-123",
        )
        self.assertEqual(
            second_call.args[0],
            "https://api-singapore.klingai.com/v1/videos/task-123",
        )


class WaitForVideoTests(unittest.TestCase):
    @patch("app.modules.ad_factory.kling_client.get_task_status")
    def test_wait_for_video_reads_task_result_videos(self, mock_get_task_status: Mock) -> None:
        mock_get_task_status.return_value = {
            "data": {
                "task_status": "succeed",
                "task_result": {"videos": [{"url": "https://cdn.example.com/video.mp4"}]},
            }
        }

        url = kling_client.wait_for_video("task-123", poll_interval=0, max_wait=1)

        self.assertEqual(url, "https://cdn.example.com/video.mp4")


if __name__ == "__main__":
    unittest.main()
