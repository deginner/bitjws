import json
import time
import bitjws
import pytest

def test_encode_decode():
    key = bitjws.PrivateKey()

    ser = bitjws.sign_serialize(key)
    header, payload = bitjws.validate_deserialize(ser)

    rawheader, rawpayload = ser.rsplit('.', 1)[0].split('.')
    origheader = bitjws.base64url_decode(rawheader.encode('utf8'))
    origpayload = bitjws.base64url_decode(rawpayload.encode('utf8'))

    assert header['typ'] == 'JWT'
    assert header['alg'] == 'CUSTOM-BITCOIN-SIGN'
    assert header['kid'] == bitjws.pubkey_to_addr(key.pubkey.serialize())
    assert len(header) == 3
    assert header == json.loads(origheader.decode('utf8'))

    assert isinstance(payload.get('exp', ''), (float, int))
    assert payload['aud'] is None
    assert len(payload) == 2
    assert payload == json.loads(origpayload.decode('utf8'))

    # Assumption: it takes mores than 0 seconds to perform the above
    # instructions but less than 1 second. 3600 is the default
    # expiration time.
    diff = 3600 - (payload['exp'] - time.time())
    assert diff > 0 and diff < 1

def test_audience():
    key = bitjws.PrivateKey()

    audience = 'https://example.com/api/login'
    ser = bitjws.sign_serialize(key, requrl=audience)
    header, payload = bitjws.validate_deserialize(ser, requrl=audience)
    assert header is not None
    assert payload is not None
    assert payload['aud'] == audience

def test_no_expire():
    key = bitjws.PrivateKey()

    ser = bitjws.sign_serialize(key, expire_after=None)
    header, payload = bitjws.validate_deserialize(ser)
    assert header is not None
    assert payload['exp'] >= 2 ** 31

def test_payload_nojson():
    key = bitjws.PrivateKey()

    ser = bitjws.sign_serialize(key)
    header64 = ser.split('.')[0]

    # Sign a new payload, 'test'
    new_payload = bitjws.base64url_encode(b'test').decode('utf8')
    signdata = '{}.{}'.format(header64, new_payload)
    sig = bitjws.ALGORITHM_AVAILABLE['CUSTOM-BITCOIN-SIGN'].sign(
        key, signdata)
    sig64 = bitjws.base64url_encode(sig).decode('utf8')

    new = '{}.{}'.format(signdata, sig64)
    with pytest.raises(bitjws.InvalidMessage):
        # The new payload was not JSON encoded, so it cannot be
        # decoded as that.
        bitjws.validate_deserialize(new)
    # But we can get its raw value.
    header, payload = bitjws.validate_deserialize(new, decode_payload=False)

    assert header is not None
    assert payload == b'test'

def test_empty():
    # This empty "test" function is here to easily allow testing
    # for missing libsecp256k1.
    #
    # py.test may be instructed to only run this test with the
    # intention to collect coverage data for `import bitjws`.
    pass


# Exercise the varint function a little bit.

def test_slightly_big():
    key = bitjws.PrivateKey()

    ser = bitjws.sign_serialize(key, test='a' * 254)
    h, p = bitjws.validate_deserialize(ser)
    assert h and p

def test_big():
    key = bitjws.PrivateKey()

    ser = bitjws.sign_serialize(key, test='a' * 65536)
    h, p = bitjws.validate_deserialize(ser)
    assert h and p
