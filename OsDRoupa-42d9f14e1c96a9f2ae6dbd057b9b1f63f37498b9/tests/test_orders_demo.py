"""Pedidos de demonstração: avanço automático, cancelamento pelo cliente e link da loja oficial (SQLite temporário)."""

import uuid
from datetime import timedelta

import pytest

from professormateria import local_backend as lb

ADMIN_API = "/api:EzKvuCov/"
ADDRESS = {"cep": "01310-100", "logradouro": "Avenida Paulista", "numero": "1000", "bairro": "Bela Vista",
           "cidade": "São Paulo", "uf": "SP", "is_default": True}


@pytest.fixture
def shopper(api):
    token = api.account()
    code, body = api.call("POST", "salvaEndereco", token, payload=ADDRESS)
    assert code == 200, body
    return token, body["endereco"]["id"]


def _product(api, token):
    """Um produto do catálogo de demonstração com estoque suficiente."""
    row = api.backend._connect().execute("SELECT id,stock FROM products WHERE active=1 AND demonstration=1 AND stock>2 ORDER BY id LIMIT 1").fetchone()
    return row["id"], row["stock"]


def _buy(api, token, address_id, product_id, qty=1):
    return api.call("POST", "checkoutPedidoDemonstrativo", token, payload={
        "chave_idempotencia": uuid.uuid4().hex, "endereco_id": address_id, "itens": [{"produto_id": product_id, "qtd": qty}]})


def _stock(api, product_id):
    return api.backend._connect().execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()["stock"]


def _age_order(api, order_id, minutes):
    created = lb._stamp(lb._now() - timedelta(minutes=minutes))
    db = api.backend._connect()
    db.execute("UPDATE orders SET created_at=? WHERE id=?", (created, order_id))
    db.commit()


def test_demo_order_starts_confirmed_and_reserves_stock(api, shopper):
    token, address_id = shopper
    product_id, stock = _product(api, token)
    code, body = _buy(api, token, address_id, product_id, 2)
    assert code == 201 and body["pedido"]["status"] == "Confirmado"
    assert _stock(api, product_id) == stock - 2


def test_demo_order_advances_until_delivered(api, shopper, monkeypatch):
    monkeypatch.setenv("OSDROUPA_DEMO_ORDER_STEP_MINUTES", "2")
    token, address_id = shopper
    product_id, stock = _product(api, token)
    order_id = _buy(api, token, address_id, product_id)[1]["pedido"]["id"]
    for minutes, expected in ((1, "Confirmado"), (2.5, "Em preparo"), (4.5, "Enviado"), (30, "Entregue")):
        _age_order(api, order_id, minutes)
        status = api.call("GET", f"meuPedido/{order_id}", token)[1]["pedido"]["status"]
        assert status == expected, (minutes, status)
    assert _stock(api, product_id) == stock - 1  # venda concluída: o estoque não volta
    row = api.backend._connect().execute("SELECT stock_reserved FROM orders WHERE id=?", (order_id,)).fetchone()
    assert row["stock_reserved"] == 0


def test_customer_cancels_before_preparation_and_stock_returns(api, shopper):
    token, address_id = shopper
    product_id, stock = _product(api, token)
    order_id = _buy(api, token, address_id, product_id, 2)[1]["pedido"]["id"]
    code, body = api.call("POST", f"cancelarPedido/{order_id}", token)
    assert code == 200 and body["pedido"]["status"] == "Cancelado"
    assert _stock(api, product_id) == stock
    assert api.call("POST", f"cancelarPedido/{order_id}", token)[0] == 409  # não cancela duas vezes
    assert _stock(api, product_id) == stock


def test_cannot_cancel_after_preparation_or_someone_elses_order(api, shopper, monkeypatch):
    monkeypatch.setenv("OSDROUPA_DEMO_ORDER_STEP_MINUTES", "2")
    token, address_id = shopper
    product_id, _ = _product(api, token)
    order_id = _buy(api, token, address_id, product_id)[1]["pedido"]["id"]
    other = api.account()
    assert api.call("POST", f"cancelarPedido/{order_id}", other)[0] == 404
    _age_order(api, order_id, 3)  # já em preparo
    assert api.call("POST", f"cancelarPedido/{order_id}", token)[0] == 409
    assert api.call("POST", f"cancelarPedido/{order_id}")[0] == 401


def test_manual_mode_keeps_admin_confirmation(api, shopper, monkeypatch):
    monkeypatch.setenv("OSDROUPA_DEMO_ORDER_AUTO", "0")
    token, address_id = shopper
    product_id, _ = _product(api, token)
    code, body = _buy(api, token, address_id, product_id)
    assert code == 201 and body["pedido"]["status"] == "Aguardando confirmação"
    order_id = body["pedido"]["id"]
    _age_order(api, order_id, 60)
    assert api.call("GET", f"meuPedido/{order_id}", token)[1]["pedido"]["status"] == "Aguardando confirmação"
    assert api.call("POST", f"cancelarPedido/{order_id}", token)[0] == 200  # também pode cancelar aguardando


# ── Link da loja oficial ────────────────────────────────────────────────────
def _admin(api):
    return api.account("admin@teste.osdroupa")


NEW_PRODUCT = {"Nome": "Camisa teste", "Categoria": "Roupas", "Preco": "99,90", "Qtd_Disp": 5,
               "Url_Imagem": "/products/linen-shirt.svg"}


def test_admin_product_with_official_store_link(api):
    admin = _admin(api)
    code, body = api.call("POST", "adminProdutos", admin, payload={**NEW_PRODUCT, "Link_Loja": "https://loja.exemplo.com/camisa"}, api=ADMIN_API)
    assert code == 201 and body["Link_Loja"] == "https://loja.exemplo.com/camisa"
    code, body = api.call("PATCH", f"adminProdutos/{body['id']}", admin, payload={"Link_Loja": ""}, api=ADMIN_API)
    assert code == 200 and body["Link_Loja"] == ""


@pytest.mark.parametrize("link", ["http://loja.exemplo.com/x", "javascript:alert(1)", "https://user:senha@loja.com/x",
                                  "https://loja.com/com espaço", "loja.com/x"])
def test_invalid_store_links_are_rejected(api, link):
    assert api.call("POST", "adminProdutos", _admin(api), payload={**NEW_PRODUCT, "Link_Loja": link}, api=ADMIN_API)[0] == 400


def test_product_with_store_link_is_not_sold_in_app(api, shopper):
    token, address_id = shopper
    code, body = api.call("POST", "adminProdutos", _admin(api), payload={**NEW_PRODUCT, "Link_Loja": "https://loja.exemplo.com/camisa"}, api=ADMIN_API)
    code, body = _buy(api, token, address_id, body["id"])
    assert code == 409 and "loja oficial" in body["message"]


def test_frontend_cancel_rule_matches_backend():
    from OSDroupa.OSDroupa import _order_cancellable
    assert _order_cancellable({"status": "Confirmado", "provedor": "Sem cobrança", "paid": False})
    assert _order_cancellable({"status": "Aguardando confirmação", "provedor": "Sem cobrança", "paid": False})
    assert not _order_cancellable({"status": "Em preparo", "provedor": "Sem cobrança", "paid": False})
    assert not _order_cancellable({"status": "Confirmado", "provedor": "Mercado Pago", "paid": False})
    assert not _order_cancellable({"status": "Confirmado", "provedor": "Sem cobrança", "paid": True})
