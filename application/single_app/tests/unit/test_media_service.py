# test_media_service.py
# Unit tests for services/media_service.py — media processing utilities.

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.usefixtures('set_test_env')
class TestGetContentType:
    """Tests for _get_content_type()."""

    def test_wav_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/file.wav') == 'audio/wav'

    def test_mp3_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/file.mp3') == 'audio/mpeg'

    def test_m4a_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/file.m4a') == 'audio/mp4'

    def test_mp4_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/file.mp4') == 'audio/mp4'

    def test_unknown_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/file.xyz') == 'application/octet-stream'

    def test_no_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('noext') == 'application/octet-stream'

    def test_uppercase_extension(self):
        """Extension matching uses .lower(), so uppercase should work."""
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/FILE.WAV') == 'audio/wav'

    def test_mixed_case_extension(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/path/to/audio.Mp3') == 'audio/mpeg'

    def test_full_path_with_directories(self):
        from services.media_service import _get_content_type
        assert _get_content_type('/home/user/uploads/recordings/test.wav') == 'audio/wav'

    def test_dot_in_filename(self):
        """File with multiple dots should use last extension."""
        from services.media_service import _get_content_type
        assert _get_content_type('audio.backup.mp3') == 'audio/mpeg'

    def test_empty_string(self):
        from services.media_service import _get_content_type
        assert _get_content_type('') == 'application/octet-stream'


@pytest.mark.usefixtures('set_test_env')
class TestGetSpeechConfig:
    """Tests for _get_speech_config(settings, endpoint, locale) — speech SDK configuration."""

    def test_returns_config_with_api_key(self):
        """Should create speech config with subscription key when auth type is api_key."""
        mock_config = MagicMock()
        settings = {
            'speech_service_authentication_type': 'api_key',
            'speech_service_key': 'test-speech-key',
        }
        with patch('services.media_service.speechsdk') as mock_sdk, \
             patch('services.media_service.debug_print'):
            mock_sdk.SpeechConfig.return_value = mock_config
            from services.media_service import _get_speech_config
            result = _get_speech_config(settings, 'https://eastus.api.cognitive.microsoft.com', 'en-US')
            assert result == mock_config
            mock_sdk.SpeechConfig.assert_called_once_with(
                endpoint='https://eastus.api.cognitive.microsoft.com',
                subscription='test-speech-key'
            )
            assert mock_config.speech_recognition_language == 'en-US'

    def test_returns_config_with_managed_identity(self):
        """Should create speech config using managed identity token."""
        mock_config = MagicMock()
        mock_token = MagicMock()
        mock_token.token = 'fake-token-value'
        settings = {
            'speech_service_authentication_type': 'managed_identity',
        }
        with patch('services.media_service.speechsdk') as mock_sdk, \
             patch('services.media_service.DefaultAzureCredential') as mock_cred_cls, \
             patch('services.media_service.cognitive_services_scope', 'https://cognitiveservices.azure.com/.default', create=True), \
             patch('services.media_service.debug_print'):
            mock_cred_cls.return_value.get_token.return_value = mock_token
            mock_sdk.SpeechConfig.return_value = mock_config
            from services.media_service import _get_speech_config
            result = _get_speech_config(settings, 'https://eastus.api.cognitive.microsoft.com', 'fr-FR')
            assert result == mock_config
            mock_sdk.SpeechConfig.assert_called_once_with(
                endpoint='https://eastus.api.cognitive.microsoft.com'
            )
            assert mock_config.authorization_token == 'fake-token-value'
            assert mock_config.speech_recognition_language == 'fr-FR'

    def test_sets_locale_on_config(self):
        """Should set speech_recognition_language to the provided locale."""
        mock_config = MagicMock()
        settings = {
            'speech_service_authentication_type': 'api_key',
            'speech_service_key': 'key',
        }
        with patch('services.media_service.speechsdk') as mock_sdk, \
             patch('services.media_service.debug_print'):
            mock_sdk.SpeechConfig.return_value = mock_config
            from services.media_service import _get_speech_config
            _get_speech_config(settings, 'https://example.com', 'ja-JP')
            assert mock_config.speech_recognition_language == 'ja-JP'


@pytest.mark.usefixtures('set_test_env')
class TestSplitAudioFile:
    """Tests for _split_audio_file() — splits audio into WAV chunks."""

    def test_successful_split(self, tmp_path):
        """Should call ffmpeg and return chunk file list."""
        input_file = str(tmp_path / "audio.mp3")
        with open(input_file, 'w') as f:
            f.write("dummy")
        # Create fake chunk files that glob will find
        for i in range(3):
            (tmp_path / f"audio_chunk_{i:03d}.wav").write_text("chunk")

        mock_ffmpeg_bin = MagicMock()
        mock_ffmpeg_py = MagicMock()
        mock_stream = MagicMock()
        mock_ffmpeg_py.input.return_value = mock_stream
        mock_stream.output.return_value = mock_stream

        with patch.dict('sys.modules', {
            'ffmpeg_binaries': mock_ffmpeg_bin,
            'ffmpeg': mock_ffmpeg_py
        }), patch('services.media_service.debug_print', create=True):
            from services.media_service import _split_audio_file
            result = _split_audio_file(input_file)
            assert len(result) == 3
            assert all('chunk' in p for p in result)

    def test_ffmpeg_failure_raises_runtime_error(self, tmp_path):
        """FFmpeg failure should raise RuntimeError."""
        input_file = str(tmp_path / "audio.mp3")
        with open(input_file, 'w') as f:
            f.write("dummy")

        mock_ffmpeg_bin = MagicMock()
        mock_ffmpeg_py = MagicMock()
        mock_stream = MagicMock()
        mock_ffmpeg_py.input.return_value = mock_stream
        mock_stream.output.return_value = mock_stream
        mock_stream.run.side_effect = Exception("FFmpeg crashed")

        with patch.dict('sys.modules', {
            'ffmpeg_binaries': mock_ffmpeg_bin,
            'ffmpeg': mock_ffmpeg_py
        }), patch('services.media_service.debug_print', create=True):
            from services.media_service import _split_audio_file
            with pytest.raises(RuntimeError, match="Segmentation failed"):
                _split_audio_file(input_file)

    def test_no_chunks_produced_raises(self, tmp_path):
        """If no WAV chunks produced, should raise RuntimeError."""
        input_file = str(tmp_path / "audio.mp3")
        with open(input_file, 'w') as f:
            f.write("dummy")

        mock_ffmpeg_bin = MagicMock()
        mock_ffmpeg_py = MagicMock()
        mock_stream = MagicMock()
        mock_ffmpeg_py.input.return_value = mock_stream
        mock_stream.output.return_value = mock_stream

        with patch.dict('sys.modules', {
            'ffmpeg_binaries': mock_ffmpeg_bin,
            'ffmpeg': mock_ffmpeg_py
        }), patch('services.media_service.debug_print', create=True):
            from services.media_service import _split_audio_file
            with pytest.raises(RuntimeError, match="No chunks produced"):
                _split_audio_file(input_file)


@pytest.mark.usefixtures('set_test_env')
class TestProcessVideoDocument:
    """Tests for process_video_document() — video processing orchestration."""

    def test_video_support_disabled_returns_zero(self, tmp_path):
        """When video support is disabled, should return 0 immediately."""
        temp_file = str(tmp_path / "video.mp4")
        with open(temp_file, 'w') as f:
            f.write("dummy video content")
        mock_callback = MagicMock()

        with patch('services.media_service.get_settings', return_value={
            'enable_video_file_support': False
        }, create=True), \
             patch('services.media_service.debug_print', create=True), \
             patch.dict('sys.modules', {
                 'functions_content': MagicMock()
             }):
            from services.media_service import process_video_document
            result = process_video_document(
                document_id='doc-1',
                user_id='user-1',
                temp_file_path=temp_file,
                original_filename='video.mp4',
                update_callback=mock_callback,
                group_id=None,
                public_workspace_id=None
            )
            assert result == 0
            mock_callback.assert_called()


@pytest.mark.usefixtures('set_test_env')
class TestProcessAudioDocument:
    """Tests for process_audio_document() — audio transcription orchestration."""

    def test_file_too_large_raises_value_error(self, tmp_path):
        """Audio files exceeding 300MB should raise ValueError."""
        temp_file = str(tmp_path / "large_audio.mp3")
        with open(temp_file, 'wb') as f:
            # Write 301MB
            f.seek(301 * 1024 * 1024)
            f.write(b'\0')
        mock_callback = MagicMock()

        with patch('services.media_service.get_settings', return_value={
            'enable_enhanced_citations': False
        }, create=True), \
             patch('services.media_service.debug_print', create=True):
            from services.media_service import process_audio_document
            with pytest.raises(ValueError, match="300 MB"):
                process_audio_document(
                    document_id='doc-1',
                    user_id='user-1',
                    temp_file_path=temp_file,
                    original_filename='large_audio.mp3',
                    update_callback=mock_callback
                )
