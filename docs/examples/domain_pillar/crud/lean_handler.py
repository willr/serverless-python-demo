import os
from http import HTTPStatus
from typing import Any, Dict

from aws_lambda_powertools.utilities.parser import ValidationError, parse

from product.crud.domain_logic.handle_create_request import handle_create_request
from product.crud.handlers.utils.http_responses import build_response
from product.crud.handlers.utils.observability import logger
from product.crud.schemas.input import CreateProductRequest
from product.crud.schemas.output import CreateProductOutput


def create_product(event, context) -> Dict[str, Any]:
    try:
        create_input: CreateProductRequest = parse(event=event, model=CreateProductRequest)
        logger.info('got create product request', extra={'product': create_input.model_dump()})
    except (ValidationError, TypeError) as exc:
        logger.exception('failed to parse input', extra={'exception': str(exc)})
        return build_response(http_status=HTTPStatus.BAD_REQUEST, body={})

    try:
        response: CreateProductOutput = handle_create_request(
            product_id=create_input.pathParameters.product,
            product_name=create_input.body.name,
            product_price=create_input.body.price,
            table_name=os.getenv('TABLE_NAME', ''),
        )
    except Exception:
        logger.exception('caught an internal error')
        return build_response(http_status=HTTPStatus.INTERNAL_SERVER_ERROR, body={})

    logger.info('finished handling create product request')
    return build_response(http_status=HTTPStatus.OK, body=response.model_dump())