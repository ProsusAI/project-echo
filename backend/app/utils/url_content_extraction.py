import logging
import re
import boto3
import json
import urllib3.util
import urllib3.exceptions
import ipaddress

from typing import List, Tuple, Dict, Union
from app.utils.url_valid_domains import get_valid_domains, valid_schemes

LAMBDA_NAME = "url-resolver-service"
WEB_URL_REGEX = re.compile(r"<(|https?://)([^<>|]+[^<>|])(|\|[^>]*?)>")


def extract_text_from_urls(urls: List[str]) -> Union[None, List[dict]]:
    """
    Extracts the content from a list of urls, utilizing plusone-url-resolver lambda.
    :param urls: list of valid or invalid urls.
    :return: dict following the schema of UrlContentListResponse, e.g.:
        {
        "responses": [
            {
                "url_content": {
                    "url": "https://en.wikipedia.org/wiki/Gabrnik,_%C5%A0kocjan",
                    "decoded_content":"blah blah blah"
                    "private": false
                },
                "success": true,
                "reason": null
            },
            {
                "url_content": {
                    "url": "https://naspers-ai-team.atlassian.net/wiki/spaces/PAI/pages/3052240909/Data+Analyst",
                    "decoded_content": "blah blah blah",
                    "private": true
                },
                "success": true,
                "reason": null
            }
        ],
        "success": true,
        "reason": null
    }
    """
    payload = {
        "urls": urls,
        "secrets_id": "NA"
    }
    logging.info(f"Extracting content from urls: {urls}, {payload}")
    # A bunch of error handling
    try:
        lambda_client = boto3.client('lambda',
                                     region_name='eu-west-1')
        response = lambda_client.invoke(
            FunctionName=LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
    except Exception as e:
        logging.error(f"Could not invoke lambda, error: {str(e)}")
        return None
    if response['StatusCode'] != 200:
        logging.error(f"Resolver Lambda invocation failed, status code: {response['StatusCode']}")
        return None
    try:
        parsed_data = json.loads(response['Payload'].read().decode())
    except Exception as e:
        logging.error(f"Could not parse resolver lambda response, error: {str(e)}")
        return None
    if not parsed_data.get("success", False):
        error_parsed_data = {k: v for k, v in parsed_data.items() if k in {"reason", "errorMessage", "errorType"}}
        logging.error(f"Resolver lambda invocation failed)", extra=error_parsed_data)
        logging.error(f"{error_parsed_data}")
        return None
    return parsed_data.get("responses")


def is_valid_url(url: str) -> bool:
    try:
        parsed_loc = urllib3.util.parse_url(url)
    except urllib3.exceptions.LocationParseError:
        return False
    host = parsed_loc.host
    if not host:
        return False
    ip_info = maybe_make_ip_address_info(host)
    if ip_info is None and host.rsplit(".", 1)[-1] not in get_valid_domains():
        # only accept domains from a list to skip names defined on a private network
        return False
    if ip_info is not None and not ip_info.is_global:  # accept global ips but not private/broadcast ones
        return False
    if (parsed_loc.scheme or "http").lower() not in valid_schemes:  # only accept http and https
        return False
    if parsed_loc.auth:  # skip urls that include authentication details
        return False
    return True


def simple_url_to_file(simple_url: dict):
    url = simple_url["url"]
    content = simple_url["decoded_content"]

    return {
        "derived_from_url": True,
        "id": url,
        "url_private": url,
        "url_private_download": url,
        "name": url,
        "file_content": content,
        "mimetype": "content_from_url/",
        "filetype": "url_content",
        "size": len(content),
    }


def text2urls(txt: str) -> List[str]:
    out = [''.join(x[:2]) for x in re.findall(WEB_URL_REGEX, txt)]
    parsed = [urllib3.util.parse_url(x) for x in out]
    out = [x for x, y in zip(out, parsed) if y.host]
    return out


def maybe_make_ip_address_info(domain: str) -> Union[ipaddress.IPv4Address, ipaddress.IPv6Address, None]:
    try:
        return ipaddress.ip_address(domain)
    except ValueError:  # when domain is not an IP
        return None


def extract_text_from_single_url(url: str) -> Union[None, str]:
    out = extract_text_from_urls([url])
    if out is None:
        return None
    if not isinstance(out, list):
        logging.error("Unexpected return type", extra={"type": type(out), "url": url})
        return None
    if len(out) != 1:
        logging.error("Number of results", extra={"length": len(out), "url": url})
        return None
    result = out[0]
    if not result.get("success", False):
        logging.warning(f"Failed retrieval", extra={"reason": result.get("reason"), "url": url})
        return None
    result_txt = result.get("url_content", {}).get("decoded_content", None)
    if result_txt is None:
        logging.error(f"Unexpected url content", extra={"keys": result.get("url_content", {}).keys(), "url": url})
        return None
    return result_txt
