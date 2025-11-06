import pytest
from unittest.mock import Mock
from src.providers.lightning_address_provider import (
    LightningAddressProvider,
    KeysendResponse,
    LnurlResponse,
)


class TestLightningAddressProvider:
    
    def test_resolve_keysend_success(self):
        """Test successful keysend resolution"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "tag": "keysend",
            "pubkey": "02c7bb6f29f09d92d40d62d64443b688891259dea324406b4678df6235794f24bf",
            "customData": [{"customKey": "696969", "customValue": "34"}]
        }
        
        mock_requester = Mock(return_value=mock_response)
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_keysend("user@example.com")
        
        assert result is not None
        assert isinstance(result, KeysendResponse)
        assert result.pubkey == "02c7bb6f29f09d92d40d62d64443b688891259dea324406b4678df6235794f24bf"
        assert len(result.custom_data) == 1
        assert result.custom_data[0]["customKey"] == "696969"
        mock_requester.assert_called_once_with(
            "GET",
            "https://example.com/.well-known/keysend/user",
            timeout=10
        )
    
    def test_resolve_keysend_invalid_address(self):
        """Test keysend resolution with invalid address format"""
        provider = LightningAddressProvider()
        result = provider.resolve_keysend("invalid-address")
        assert result is None
    
    def test_resolve_keysend_404(self):
        """Test keysend resolution when endpoint returns 404"""
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_requester = Mock(return_value=mock_response)
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_keysend("user@example.com")
        assert result is None
    
    def test_resolve_keysend_invalid_pubkey(self):
        """Test keysend resolution with invalid pubkey"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "tag": "keysend",
            "pubkey": "not-a-valid-hex-pubkey"
        }
        
        mock_requester = Mock(return_value=mock_response)
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_keysend("user@example.com")
        assert result is None
    
    def test_resolve_lnurl_success(self):
        """Test successful LNURL resolution"""
        # Mock first request to LNURL endpoint
        mock_lnurl_response = Mock()
        mock_lnurl_response.status_code = 200
        mock_lnurl_response.json.return_value = {
            "tag": "payRequest",
            "callback": "https://example.com/lnurl/callback",
            "minSendable": 1000,
            "maxSendable": 100000000
        }
        
        # Mock second request to callback endpoint
        mock_callback_response = Mock()
        mock_callback_response.status_code = 200
        mock_callback_response.json.return_value = {
            "pr": "lnbc100n1..."
        }
        
        mock_requester = Mock(side_effect=[mock_lnurl_response, mock_callback_response])
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_lnurl("user@example.com", 10000)
        
        assert result is not None
        assert isinstance(result, LnurlResponse)
        assert result.invoice == "lnbc100n1..."
        assert mock_requester.call_count == 2
    
    def test_resolve_lnurl_amount_too_low(self):
        """Test LNURL resolution when amount is below minimum"""
        mock_lnurl_response = Mock()
        mock_lnurl_response.status_code = 200
        mock_lnurl_response.json.return_value = {
            "tag": "payRequest",
            "callback": "https://example.com/lnurl/callback",
            "minSendable": 10000,
            "maxSendable": 100000000
        }
        
        mock_requester = Mock(return_value=mock_lnurl_response)
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_lnurl("user@example.com", 1000)
        
        assert result is None
        # Should only call once (not proceed to callback)
        assert mock_requester.call_count == 1
    
    def test_resolve_lnurl_invalid_address(self):
        """Test LNURL resolution with invalid address format"""
        provider = LightningAddressProvider()
        result = provider.resolve_lnurl("invalid-address", 10000)
        assert result is None
    
    def test_resolve_lnurl_wrong_tag(self):
        """Test LNURL resolution when tag is not payRequest"""
        mock_lnurl_response = Mock()
        mock_lnurl_response.status_code = 200
        mock_lnurl_response.json.return_value = {
            "tag": "withdrawRequest",
            "callback": "https://example.com/lnurl/callback"
        }
        
        mock_requester = Mock(return_value=mock_lnurl_response)
        provider = LightningAddressProvider(requester=mock_requester)
        
        result = provider.resolve_lnurl("user@example.com", 10000)
        assert result is None

