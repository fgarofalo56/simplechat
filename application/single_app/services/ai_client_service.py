# ai_client_service.py
# AI client initialization for GPT and image generation.
# Extracted from route_backend_chats.py — Phase 4 God File Decomposition.

import logging
from typing import Any, Dict, Optional, Tuple

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from config import cognitive_services_scope
from functions_debug import debug_print
from functions_logging import log_event


def initialize_gpt_client(
    settings: Dict[str, Any],
    frontend_gpt_model: Optional[str] = None,
) -> Tuple[AzureOpenAI, str]:
    """
    Initialize GPT client and resolve model deployment name.

    Returns:
        (gpt_client, gpt_model) tuple.

    Raises:
        ValueError: If configuration is incomplete or invalid.
    """
    enable_gpt_apim = settings.get('enable_gpt_apim', False)

    if enable_gpt_apim:
        # Read raw comma-delimited deployments
        raw = settings.get('azure_apim_gpt_deployment', '')
        if not raw:
            raise ValueError("APIM GPT deployment name not configured.")

        # Split, strip, and filter out empty entries
        apim_models = [m.strip() for m in raw.split(',') if m.strip()]
        if not apim_models:
            raise ValueError("No valid APIM GPT deployment names found.")

        # If frontend specified one, use it (must be in the configured list)
        if frontend_gpt_model:
            if frontend_gpt_model not in apim_models:
                raise ValueError(
                    f"Requested model '{frontend_gpt_model}' is not configured for APIM."
                )
            gpt_model = frontend_gpt_model
        elif len(apim_models) == 1:
            gpt_model = apim_models[0]
        else:
            raise ValueError(
                "Multiple APIM GPT deployments configured; please include "
                "'model_deployment' in your request."
            )

        gpt_client = AzureOpenAI(
            api_version=settings.get('azure_apim_gpt_api_version'),
            azure_endpoint=settings.get('azure_apim_gpt_endpoint'),
            api_key=settings.get('azure_apim_gpt_subscription_key')
        )
    else:
        auth_type = settings.get('azure_openai_gpt_authentication_type')
        endpoint = settings.get('azure_openai_gpt_endpoint')
        api_version = settings.get('azure_openai_gpt_api_version')
        gpt_model_obj = settings.get('gpt_model', {})

        if gpt_model_obj and gpt_model_obj.get('selected'):
            selected_gpt_model = gpt_model_obj['selected'][0]
            gpt_model = selected_gpt_model['deploymentName']
        else:
            raise ValueError("No GPT model selected or configured.")

        if frontend_gpt_model:
            gpt_model = frontend_gpt_model
        elif gpt_model_obj and gpt_model_obj.get('selected'):
            selected_gpt_model = gpt_model_obj['selected'][0]
            gpt_model = selected_gpt_model['deploymentName']
        else:
            raise ValueError("No GPT model selected or configured.")

        if auth_type == 'managed_identity':
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), cognitive_services_scope
            )
            gpt_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider
            )
        else:
            api_key = settings.get('azure_openai_gpt_key')
            if not api_key:
                raise ValueError("Azure OpenAI API Key not configured.")
            gpt_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=api_key
            )

    if not gpt_client or not gpt_model:
        raise ValueError("GPT Client or Model could not be initialized.")

    return gpt_client, gpt_model


def initialize_image_client(
    settings: Dict[str, Any],
    frontend_image_model: Optional[str] = None,
) -> Tuple[AzureOpenAI, str]:
    """
    Initialize image generation client and resolve model deployment name.

    Returns:
        (image_client, image_model) tuple.

    Raises:
        ValueError: If configuration is incomplete or invalid.
    """
    enable_image_gen_apim = settings.get('enable_image_gen_apim', False)

    if enable_image_gen_apim:
        raw = settings.get('azure_apim_image_gen_deployment', '')
        if not raw:
            raise ValueError("APIM Image Gen deployment name not configured.")

        apim_models = [m.strip() for m in raw.split(',') if m.strip()]
        if not apim_models:
            raise ValueError("No valid APIM Image Gen deployment names found.")

        if frontend_image_model:
            if frontend_image_model not in apim_models:
                raise ValueError(
                    f"Requested image model '{frontend_image_model}' is not configured for APIM."
                )
            image_model = frontend_image_model
        elif len(apim_models) == 1:
            image_model = apim_models[0]
        else:
            raise ValueError(
                "Multiple APIM Image Gen deployments configured; please include "
                "'model_deployment' in your request."
            )

        image_client = AzureOpenAI(
            api_version=settings.get('azure_apim_image_gen_api_version'),
            azure_endpoint=settings.get('azure_apim_image_gen_endpoint'),
            api_key=settings.get('azure_apim_image_gen_subscription_key')
        )
    else:
        auth_type = settings.get('azure_openai_gpt_authentication_type')
        endpoint = settings.get('azure_openai_gpt_endpoint')
        api_version = settings.get('azure_openai_gpt_api_version')
        image_model_obj = settings.get('image_model', {})

        if image_model_obj and image_model_obj.get('selected'):
            selected_model = image_model_obj['selected'][0]
            image_model = selected_model['deploymentName']
        else:
            raise ValueError("No Image Gen model selected or configured.")

        if frontend_image_model:
            image_model = frontend_image_model

        if auth_type == 'managed_identity':
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), cognitive_services_scope
            )
            image_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider
            )
        else:
            api_key = settings.get('azure_openai_gpt_key')
            if not api_key:
                raise ValueError("Azure OpenAI API Key not configured.")
            image_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=api_key
            )

    if not image_client or not image_model:
        raise ValueError("Image Client or Model could not be initialized.")

    return image_client, image_model
