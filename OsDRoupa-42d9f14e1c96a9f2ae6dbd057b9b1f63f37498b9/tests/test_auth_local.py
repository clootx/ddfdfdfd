"""Autenticação no backend SQLite (banco temporário)."""

from conftest import AUTH_API


def test_register_login_me(api):
    token = api.account("pessoa@teste.osdroupa")
    status, me = api.call("GET", "me", token, api=AUTH_API)
    assert status == 200 and me["email"] == "pessoa@teste.osdroupa"
    assert "password_hash" not in me and "password_salt" not in me


def test_register_validations(api):
    status, _ = api.call("POST", "cadastraCliente", payload={"nome": "X", "email": "a@b.c", "celular": "1", "senha": "Senha@123", "aceitou_termos": False})
    assert status == 400
    status, _ = api.register("fraca@teste.osdroupa", password="senhafraca")
    assert status == 400
    assert api.register("dup@teste.osdroupa")[0] in (200, 201)
    assert api.register("dup@teste.osdroupa")[0] == 409


def test_login_wrong_password_and_unknown_email(api):
    api.register("x@teste.osdroupa")
    assert api.login("x@teste.osdroupa", "Errada@123")[0] == 401
    assert api.login("ninguem@teste.osdroupa")[0] == 401


def test_invalid_token_and_logout(api):
    assert api.call("GET", "me", "token-invalido", api=AUTH_API)[0] == 401
    assert api.call("GET", "buscaCliente")[0] == 401
    token = api.account()
    assert api.call("POST", "logout", token, api=AUTH_API)[0] == 200
    assert api.call("GET", "me", token, api=AUTH_API)[0] == 401


def test_admin_role_from_env(api):
    admin = api.account("admin@teste.osdroupa")
    member = api.account()
    assert api.call("GET", "adminDepoimentos", admin)[0] == 200
    assert api.call("GET", "adminDepoimentos", member)[0] == 403
