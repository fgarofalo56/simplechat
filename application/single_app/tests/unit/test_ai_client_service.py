# test_ai_client_service.py
# Unit tests for services/ai_client_service.py — GPT and image client initialization.

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.usefixtures('set_test_env')
class TestInitializeGptClient:
    """Test cases for initialize_gpt_client function."""

    def test_apim_single_deployment_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_gpt_apim': True,
            'azure_apim_gpt_deployment': 'gpt-4o',
            'azure_apim_gpt_api_version': '2024-06-01',
            'azure_apim_gpt_endpoint': 'https://apim.example.com',
            'azure_apim_gpt_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_gpt_client
            client, model = initialize_gpt_client(settings)
            assert client == mock_client
            assert model == 'gpt-4o'

    def test_apim_multiple_deployments_with_frontend_model(self):
        mock_client = MagicMock()
        settings = {
            'enable_gpt_apim': True,
            'azure_apim_gpt_deployment': 'gpt-4o, gpt-35-turbo',
            'azure_apim_gpt_api_version': '2024-06-01',
            'azure_apim_gpt_endpoint': 'https://apim.example.com',
            'azure_apim_gpt_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_gpt_client
            client, model = initialize_gpt_client(settings, frontend_gpt_model='gpt-35-turbo')
            assert model == 'gpt-35-turbo'

    def test_apim_multiple_without_frontend_raises(self):
        settings = {
            'enable_gpt_apim': True,
            'azure_apim_gpt_deployment': 'gpt-4o, gpt-35-turbo',
            'azure_apim_gpt_api_version': '2024-06-01',
            'azure_apim_gpt_endpoint': 'https://apim.example.com',
            'azure_apim_gpt_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_gpt_client
            with pytest.raises(ValueError, match="Multiple APIM GPT deployments"):
                initialize_gpt_client(settings)

    def test_apim_frontend_not_in_list_raises(self):
        settings = {
            'enable_gpt_apim': True,
            'azure_apim_gpt_deployment': 'gpt-4o, gpt-35-turbo',
            'azure_apim_gpt_api_version': '2024-06-01',
            'azure_apim_gpt_endpoint': 'https://apim.example.com',
            'azure_apim_gpt_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_gpt_client
            with pytest.raises(ValueError, match="not configured for APIM"):
                initialize_gpt_client(settings, frontend_gpt_model='gpt-nonexistent')

    def test_apim_empty_deployment_raises(self):
        settings = {
            'enable_gpt_apim': True,
            'azure_apim_gpt_deployment': '',
            'azure_apim_gpt_api_version': '2024-06-01',
            'azure_apim_gpt_endpoint': 'https://apim.example.com',
            'azure_apim_gpt_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_gpt_client
            with pytest.raises(ValueError, match="APIM GPT deployment name not configured"):
                initialize_gpt_client(settings)

    def test_non_apim_api_key_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_gpt_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-api-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'gpt_model': {
                'selected': [{'deploymentName': 'my-gpt-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_gpt_client
            client, model = initialize_gpt_client(settings)
            assert client == mock_client
            assert model == 'my-gpt-deployment'

    def test_non_apim_managed_identity_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_gpt_apim': False,
            'azure_openai_gpt_authentication_type': 'managed_identity',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'gpt_model': {
                'selected': [{'deploymentName': 'my-gpt-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client), \
             patch('services.ai_client_service.DefaultAzureCredential'), \
             patch('services.ai_client_service.get_bearer_token_provider', return_value=MagicMock()), \
             patch('services.ai_client_service.cognitive_services_scope', 'https://cognitiveservices.azure.com/.default'):
            from services.ai_client_service import initialize_gpt_client
            client, model = initialize_gpt_client(settings)
            assert client == mock_client
            assert model == 'my-gpt-deployment'

    def test_non_apim_no_model_selected_raises(self):
        settings = {
            'enable_gpt_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-api-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'gpt_model': {'selected': []}
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_gpt_client
            with pytest.raises(ValueError, match="No GPT model selected"):
                initialize_gpt_client(settings)

    def test_non_apim_no_api_key_raises(self):
        settings = {
            'enable_gpt_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': '',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'gpt_model': {
                'selected': [{'deploymentName': 'my-gpt-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_gpt_client
            with pytest.raises(ValueError, match="Azure OpenAI API Key not configured"):
                initialize_gpt_client(settings)

    def test_non_apim_frontend_model_overrides(self):
        mock_client = MagicMock()
        settings = {
            'enable_gpt_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'gpt_model': {
                'selected': [{'deploymentName': 'original-model'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_gpt_client
            client, model = initialize_gpt_client(settings, frontend_gpt_model='override-model')
            assert model == 'override-model'


@pytest.mark.usefixtures('set_test_env')
class TestInitializeImageClient:
    """Test cases for initialize_image_client function."""

    def test_apim_single_deployment_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_image_gen_apim': True,
            'azure_apim_image_gen_deployment': 'dall-e-3',
            'azure_apim_image_gen_api_version': '2024-06-01',
            'azure_apim_image_gen_endpoint': 'https://apim.example.com',
            'azure_apim_image_gen_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_image_client
            client, model = initialize_image_client(settings)
            assert client == mock_client
            assert model == 'dall-e-3'

    def test_apim_frontend_model_not_in_list_raises(self):
        settings = {
            'enable_image_gen_apim': True,
            'azure_apim_image_gen_deployment': 'dall-e-3, dall-e-2',
            'azure_apim_image_gen_api_version': '2024-06-01',
            'azure_apim_image_gen_endpoint': 'https://apim.example.com',
            'azure_apim_image_gen_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_image_client
            with pytest.raises(ValueError, match="not configured for APIM"):
                initialize_image_client(settings, frontend_image_model='midjourney')

    def test_apim_empty_deployment_raises(self):
        settings = {
            'enable_image_gen_apim': True,
            'azure_apim_image_gen_deployment': '',
            'azure_apim_image_gen_api_version': '2024-06-01',
            'azure_apim_image_gen_endpoint': 'https://apim.example.com',
            'azure_apim_image_gen_subscription_key': 'test-key'
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_image_client
            with pytest.raises(ValueError, match="APIM Image Gen deployment name not configured"):
                initialize_image_client(settings)

    def test_non_apim_api_key_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_image_gen_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-api-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'image_model': {
                'selected': [{'deploymentName': 'my-dalle-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_image_client
            client, model = initialize_image_client(settings)
            assert client == mock_client
            assert model == 'my-dalle-deployment'

    def test_non_apim_managed_identity_succeeds(self):
        mock_client = MagicMock()
        settings = {
            'enable_image_gen_apim': False,
            'azure_openai_gpt_authentication_type': 'managed_identity',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'image_model': {
                'selected': [{'deploymentName': 'my-dalle-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client), \
             patch('services.ai_client_service.DefaultAzureCredential'), \
             patch('services.ai_client_service.get_bearer_token_provider', return_value=MagicMock()), \
             patch('services.ai_client_service.cognitive_services_scope', 'https://cognitiveservices.azure.com/.default'):
            from services.ai_client_service import initialize_image_client
            client, model = initialize_image_client(settings)
            assert client == mock_client
            assert model == 'my-dalle-deployment'

    def test_non_apim_no_model_selected_raises(self):
        settings = {
            'enable_image_gen_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'image_model': {'selected': []}
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_image_client
            with pytest.raises(ValueError, match="No Image Gen model selected"):
                initialize_image_client(settings)

    def test_non_apim_no_api_key_raises(self):
        settings = {
            'enable_image_gen_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': '',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'image_model': {
                'selected': [{'deploymentName': 'my-dalle-deployment'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI'):
            from services.ai_client_service import initialize_image_client
            with pytest.raises(ValueError, match="Azure OpenAI API Key not configured"):
                initialize_image_client(settings)

    def test_non_apim_frontend_model_overrides(self):
        mock_client = MagicMock()
        settings = {
            'enable_image_gen_apim': False,
            'azure_openai_gpt_authentication_type': 'api_key',
            'azure_openai_gpt_key': 'test-key',
            'azure_openai_gpt_api_version': '2024-06-01',
            'azure_openai_gpt_endpoint': 'https://openai.example.com',
            'image_model': {
                'selected': [{'deploymentName': 'original-dalle'}]
            }
        }
        with patch('services.ai_client_service.AzureOpenAI', return_value=mock_client):
            from services.ai_client_service import initialize_image_client
            client, model = initialize_image_client(settings, frontend_image_model='override-dalle')
            assert model == 'override-dalle'
