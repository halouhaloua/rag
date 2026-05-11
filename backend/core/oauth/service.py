#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: service.py
@Desc: OAuth Service - OAuth 业务逻辑层 - 处理第三方 OAuth 登录逻辑（异步版本）
"""
"""
OAuth Service - OAuth 业务逻辑层
处理第三方 OAuth 登录逻辑（异步版本）
"""
import json
import logging
import re
from typing import Dict, Optional

import httpx

from app.config import settings
from core.oauth.base_oauth_service import BaseOAuthService

logger = logging.getLogger(__name__)


class GiteeOAuthService(BaseOAuthService):
    """Gitee OAuth 服务类"""

    PROVIDER_NAME = 'gitee'
    AUTHORIZE_URL = "https://gitee.com/oauth/authorize"
    TOKEN_URL = "https://gitee.com/oauth/token"
    USER_INFO_URL = "https://gitee.com/api/v5/user"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取 Gitee 客户端配置"""
        return {
            'client_id': getattr(settings, 'GITEE_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'GITEE_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'GITEE_REDIRECT_URI', ''),
        }

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """
        使用访问令牌获取 Gitee 用户信息
        """
        try:
            params = {'access_token': access_token}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, params=params)
                response.raise_for_status()

                user_info = response.json()

                if 'id' not in user_info:
                    logger.error(f"Gitee 用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求 Gitee 用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 Gitee 用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化 Gitee 用户信息"""
        return {
            'provider_id': str(raw_user_info.get('id')),
            'username': raw_user_info.get('login'),
            'name': raw_user_info.get('name', raw_user_info.get('login')),
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('avatar_url'),
            'bio': raw_user_info.get('bio'),
        }


class GitHubOAuthService(BaseOAuthService):
    """GitHub OAuth 服务类"""

    PROVIDER_NAME = 'github'
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_INFO_URL = "https://api.github.com/user"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取 GitHub 客户端配置"""
        return {
            'client_id': getattr(settings, 'GITHUB_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'GITHUB_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'GITHUB_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """GitHub 需要 scope 参数"""
        return {
            'scope': 'user:email',
        }

    @classmethod
    def get_token_request_headers(cls) -> Dict[str, str]:
        """GitHub 需要 Accept header 来获取 JSON 响应"""
        return {
            'Accept': 'application/json',
        }

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用访问令牌获取 GitHub 用户信息"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json',
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                if 'id' not in user_info:
                    logger.error(f"GitHub 用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求 GitHub 用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 GitHub 用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化 GitHub 用户信息"""
        return {
            'provider_id': str(raw_user_info.get('id')),
            'username': raw_user_info.get('login'),
            'name': raw_user_info.get('name') or raw_user_info.get('login'),
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('avatar_url'),
            'bio': raw_user_info.get('bio'),
        }


class QQOAuthService(BaseOAuthService):
    """QQ 互联 OAuth 服务类"""

    PROVIDER_NAME = 'qq'
    AUTHORIZE_URL = "https://graph.qq.com/oauth2.0/authorize"
    TOKEN_URL = "https://graph.qq.com/oauth2.0/token"
    USER_INFO_URL = "https://graph.qq.com/user/get_user_info"
    OPENID_URL = "https://graph.qq.com/oauth2.0/me"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取 QQ 客户端配置"""
        return {
            'client_id': getattr(settings, 'QQ_APP_ID', ''),
            'client_secret': getattr(settings, 'QQ_APP_KEY', ''),
            'redirect_uri': getattr(settings, 'QQ_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """QQ 需要 response_type 参数"""
        return {
            'response_type': 'code',
        }

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[str]:
        """使用授权码获取访问令牌（QQ 返回 URL 参数格式）"""
        try:
            config = cls.get_client_config()

            params = {
                'grant_type': 'authorization_code',
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': config['redirect_uri'],
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.TOKEN_URL, params=params)
                response.raise_for_status()

                # QQ 返回的是 URL 参数格式: access_token=xxx&expires_in=xxx
                response_text = response.text

                match = re.search(r'access_token=([^&]+)', response_text)
                if match:
                    access_token = match.group(1)
                    logger.info(f"QQ access_token 获取成功")
                    return access_token
                else:
                    logger.error(f"QQ access_token 解析失败: {response_text}")
                    return None

        except httpx.RequestError as e:
            logger.error(f"请求 QQ access_token 失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 QQ access_token 异常: {str(e)}")
            return None

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用访问令牌获取 QQ 用户信息"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. 获取 openid
                openid_response = await client.get(
                    cls.OPENID_URL,
                    params={'access_token': access_token}
                )
                openid_response.raise_for_status()

                # QQ 返回的是 JSONP 格式: callback( {"client_id":"xxx","openid":"xxx"} );
                openid_text = openid_response.text

                match = re.search(r'callback\(\s*(\{.*?\})\s*\)', openid_text)
                if not match:
                    logger.error(f"QQ openid 解析失败: {openid_text}")
                    return None

                openid_data = json.loads(match.group(1))
                openid = openid_data.get('openid')

                if not openid:
                    logger.error(f"QQ openid 不存在: {openid_data}")
                    return None

                logger.info(f"QQ openid 获取成功: {openid}")

                # 2. 获取用户信息
                config = cls.get_client_config()
                user_response = await client.get(
                    cls.USER_INFO_URL,
                    params={
                        'access_token': access_token,
                        'oauth_consumer_key': config['client_id'],
                        'openid': openid
                    }
                )
                user_response.raise_for_status()

                user_info = user_response.json()

                if user_info.get('ret') != 0:
                    logger.error(f"QQ 用户信息获取失败: {user_info.get('msg')}")
                    return None

                user_info['openid'] = openid
                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求 QQ 用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 QQ 用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化 QQ 用户信息"""
        return {
            'provider_id': raw_user_info.get('openid'),
            'username': raw_user_info.get('nickname', '').replace(' ', '_'),
            'name': raw_user_info.get('nickname'),
            'email': None,
            'avatar': raw_user_info.get('figureurl_qq_2') or raw_user_info.get('figureurl_qq_1'),
            'bio': None,
        }


class GoogleOAuthService(BaseOAuthService):
    """Google OAuth 服务类"""

    PROVIDER_NAME = 'google'
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取 Google 客户端配置"""
        return {
            'client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'GOOGLE_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """Google 需要 scope 和 access_type 参数"""
        return {
            'scope': 'openid email profile',
            'access_type': 'offline',
            'response_type': 'code',
        }

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用访问令牌获取 Google 用户信息"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                if 'id' not in user_info:
                    logger.error(f"Google 用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求 Google 用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 Google 用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化 Google 用户信息"""
        return {
            'provider_id': raw_user_info.get('id'),
            'username': raw_user_info.get('email', '').split('@')[0],
            'name': raw_user_info.get('name') or raw_user_info.get('email'),
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('picture'),
            'bio': None,
        }


class WeChatOAuthService(BaseOAuthService):
    """微信开放平台 OAuth 服务类"""

    PROVIDER_NAME = 'wechat'
    AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
    TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"

    @classmethod
    def get_user_id_field(cls) -> str:
        """微信使用 unionid 作为唯一标识"""
        return 'wechat_unionid'

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取微信客户端配置"""
        return {
            'client_id': getattr(settings, 'WECHAT_APP_ID', ''),
            'client_secret': getattr(settings, 'WECHAT_APP_SECRET', ''),
            'redirect_uri': getattr(settings, 'WECHAT_REDIRECT_URI', ''),
        }

    @classmethod
    def get_authorize_url(cls, state: str = None) -> str:
        """获取微信授权 URL（微信参数名称与标准 OAuth 2.0 不同）"""
        config = cls.get_client_config()

        params = {
            'appid': config['client_id'],
            'redirect_uri': config['redirect_uri'],
            'response_type': 'code',
            'scope': 'snsapi_login',
        }

        if state:
            params['state'] = state

        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{cls.AUTHORIZE_URL}?{query_string}#wechat_redirect"

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[Dict]:
        """使用授权码获取访问令牌（微信返回 access_token 和 openid）"""
        try:
            config = cls.get_client_config()
            params = {
                'appid': config['client_id'],
                'secret': config['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.TOKEN_URL, params=params)
                response.raise_for_status()

                token_data = response.json()

                if 'errcode' in token_data:
                    logger.error(f"微信获取 token 失败: {token_data}")
                    return None

                if 'access_token' not in token_data or 'openid' not in token_data:
                    logger.error(f"微信 token 响应格式错误: {token_data}")
                    return None

                return token_data

        except httpx.RequestError as e:
            logger.error(f"请求微信 token 失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取微信 token 异常: {str(e)}")
            return None

    @classmethod
    async def get_user_info(cls, access_token: str, openid: str = None) -> Optional[Dict]:
        """使用访问令牌获取微信用户信息"""
        try:
            params = {
                'access_token': access_token,
                'openid': openid,
                'lang': 'zh_CN',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, params=params)
                response.raise_for_status()

                user_info = response.json()

                if 'errcode' in user_info:
                    logger.error(f"微信获取用户信息失败: {user_info}")
                    return None

                if 'openid' not in user_info:
                    logger.error(f"微信用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求微信用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取微信用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化微信用户信息"""
        provider_id = raw_user_info.get('unionid') or raw_user_info.get('openid')
        nickname = raw_user_info.get('nickname', '')
        username = nickname.replace(' ', '_')[:30] if nickname else f"wechat_{provider_id[:8]}"

        return {
            'provider_id': provider_id,
            'username': username,
            'name': nickname or username,
            'email': None,
            'avatar': raw_user_info.get('headimgurl'),
            'bio': None,
        }


class MicrosoftOAuthService(BaseOAuthService):
    """微软 OAuth 服务类"""

    PROVIDER_NAME = 'microsoft'
    AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USER_INFO_URL = "https://graph.microsoft.com/v1.0/me"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取微软客户端配置"""
        return {
            'client_id': getattr(settings, 'MICROSOFT_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'MICROSOFT_CLIENT_SECRET', ''),
            'redirect_uri': getattr(settings, 'MICROSOFT_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """微软需要 scope 和 response_mode 参数"""
        return {
            'scope': 'openid email profile User.Read',
            'response_type': 'code',
            'response_mode': 'query',
        }

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用 Microsoft Graph API 获取用户信息"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                if 'id' not in user_info:
                    logger.error(f"Microsoft 用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求 Microsoft 用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取 Microsoft 用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化微软用户信息"""
        user_principal_name = raw_user_info.get('userPrincipalName', '')
        username = user_principal_name.split('@')[0] if '@' in user_principal_name else user_principal_name
        email = raw_user_info.get('mail') or raw_user_info.get('userPrincipalName')

        return {
            'provider_id': raw_user_info.get('id'),
            'username': username or f"ms_{raw_user_info.get('id', '')[:8]}",
            'name': raw_user_info.get('displayName') or username,
            'email': email,
            'avatar': None,
            'bio': raw_user_info.get('jobTitle'),
        }


class DingTalkOAuthService(BaseOAuthService):
    """钉钉 OAuth 服务类"""

    PROVIDER_NAME = 'dingtalk'
    AUTHORIZE_URL = "https://login.dingtalk.com/oauth2/auth"
    TOKEN_URL = "https://api.dingtalk.com/v1.0/oauth2/userAccessToken"
    USER_INFO_URL = "https://api.dingtalk.com/v1.0/contact/users/me"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取钉钉客户端配置"""
        return {
            'client_id': getattr(settings, 'DINGTALK_APP_ID', ''),
            'client_secret': getattr(settings, 'DINGTALK_APP_SECRET', ''),
            'redirect_uri': getattr(settings, 'DINGTALK_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """钉钉需要的额外授权参数"""
        return {
            'response_type': 'code',
            'scope': 'openid',
            'prompt': 'consent',
        }

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[str]:
        """使用授权码获取访问令牌（钉钉使用 JSON body）"""
        try:
            config = cls.get_client_config()

            data = {
                'clientId': config['client_id'],
                'clientSecret': config['client_secret'],
                'code': code,
                'grantType': 'authorization_code',
            }

            headers = {
                'Content-Type': 'application/json',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(cls.TOKEN_URL, json=data, headers=headers)
                response.raise_for_status()

                result = response.json()

                if 'accessToken' in result:
                    logger.info(f"钉钉 access_token 获取成功")
                    return result['accessToken']
                else:
                    logger.error(f"钉钉 token 响应格式错误: {result}")
                    return None

        except httpx.RequestError as e:
            logger.error(f"请求钉钉 access_token 失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取钉钉 access_token 异常: {str(e)}")
            return None

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用访问令牌获取钉钉用户信息"""
        try:
            headers = {
                'x-acs-dingtalk-access-token': access_token,
                'Content-Type': 'application/json',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, headers=headers)
                response.raise_for_status()

                user_info = response.json()

                if 'unionId' not in user_info:
                    logger.error(f"钉钉用户信息格式错误: {user_info}")
                    return None

                return user_info

        except httpx.RequestError as e:
            logger.error(f"请求钉钉用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取钉钉用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化钉钉用户信息"""
        provider_id = raw_user_info.get('unionId', '')
        nick = raw_user_info.get('nick', '')
        username = nick if nick else f"dingtalk_{provider_id[:8]}"

        return {
            'provider_id': provider_id,
            'username': username,
            'name': nick or username,
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('avatarUrl'),
            'mobile': raw_user_info.get('mobile'),
            'bio': f"钉钉用户 - {nick}" if nick else "钉钉用户",
        }

    @classmethod
    def get_user_id_field(cls) -> str:
        """获取用户 ID 字段名"""
        return 'dingtalk_unionid'


class FeishuOAuthService(BaseOAuthService):
    """飞书 OAuth 服务类"""

    PROVIDER_NAME = 'feishu'
    AUTHORIZE_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"
    TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"
    USER_INFO_URL = "https://open.feishu.cn/open-apis/authen/v1/user_info"

    @classmethod
    def get_client_config(cls) -> Dict[str, str]:
        """获取飞书客户端配置"""
        return {
            'client_id': getattr(settings, 'FEISHU_APP_ID', ''),
            'client_secret': getattr(settings, 'FEISHU_APP_SECRET', ''),
            'redirect_uri': getattr(settings, 'FEISHU_REDIRECT_URI', ''),
        }

    @classmethod
    def get_extra_authorize_params(cls) -> Dict[str, str]:
        """飞书需要的额外授权参数"""
        return {
            'response_type': 'code',
            'scope': 'contact:user.base:readonly',
        }

    @classmethod
    async def _get_app_access_token(cls) -> Optional[str]:
        """获取应用级别的 access_token"""
        try:
            config = cls.get_client_config()

            url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
            data = {
                'app_id': config['client_id'],
                'app_secret': config['client_secret'],
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=data)
                response.raise_for_status()

                result = response.json()

                if result.get('code') == 0:
                    return result.get('app_access_token')

                logger.error(f"获取飞书 app_access_token 失败: {result}")
                return None

        except Exception as e:
            logger.error(f"获取飞书 app_access_token 异常: {str(e)}")
            return None

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[str]:
        """使用授权码获取访问令牌"""
        try:
            app_access_token = await cls._get_app_access_token()
            if not app_access_token:
                return None

            data = {
                'grant_type': 'authorization_code',
                'code': code,
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {app_access_token}',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(cls.TOKEN_URL, json=data, headers=headers)
                response.raise_for_status()

                result = response.json()

                if result.get('code') == 0 and 'data' in result:
                    access_token = result['data'].get('access_token')
                    if access_token:
                        logger.info(f"飞书 access_token 获取成功")
                        return access_token

                logger.error(f"飞书 token 响应格式错误: {result}")
                return None

        except httpx.RequestError as e:
            logger.error(f"请求飞书 access_token 失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取飞书 access_token 异常: {str(e)}")
            return None

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[Dict]:
        """使用访问令牌获取飞书用户信息"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cls.USER_INFO_URL, headers=headers)
                response.raise_for_status()

                result = response.json()

                if result.get('code') == 0 and 'data' in result:
                    user_info = result['data']
                    if 'union_id' not in user_info:
                        logger.error(f"飞书用户信息格式错误: {result}")
                        return None
                    return user_info

                logger.error(f"飞书用户信息响应错误: {result}")
                return None

        except httpx.RequestError as e:
            logger.error(f"请求飞书用户信息失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"获取飞书用户信息异常: {str(e)}")
            return None

    @classmethod
    def normalize_user_info(cls, raw_user_info: Dict) -> Dict:
        """标准化飞书用户信息"""
        provider_id = raw_user_info.get('union_id', '')
        name = raw_user_info.get('name', '')
        en_name = raw_user_info.get('en_name', '')
        username = en_name or name or f"feishu_{provider_id[:8]}"
        username = username.replace(' ', '_')

        mobile = raw_user_info.get('mobile', '')
        if mobile and mobile.startswith('+86-'):
            mobile = mobile[4:]

        return {
            'provider_id': provider_id,
            'username': username,
            'name': name or username,
            'email': raw_user_info.get('email'),
            'avatar': raw_user_info.get('avatar_url') or raw_user_info.get('avatar_big'),
            'mobile': mobile,
            'bio': f"飞书用户 - {name}" if name else "飞书用户",
        }

    @classmethod
    def get_user_id_field(cls) -> str:
        """获取用户 ID 字段名"""
        return 'feishu_union_id'


# OAuth 提供商映射
OAUTH_PROVIDERS = {
    'gitee': GiteeOAuthService,
    'github': GitHubOAuthService,
    'qq': QQOAuthService,
    'google': GoogleOAuthService,
    'wechat': WeChatOAuthService,
    'microsoft': MicrosoftOAuthService,
    'dingtalk': DingTalkOAuthService,
    'feishu': FeishuOAuthService,
}
