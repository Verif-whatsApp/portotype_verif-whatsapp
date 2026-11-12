"""Garde-fou : chaque module du projet doit pouvoir être importé.

Un import cassé (fichier oublié dans un commit, nom renommé) passait inaperçu tant qu'aucun
test n'importait le module concerné.
"""

import importlib
import pkgutil

import app


def test_every_module_of_the_application_can_be_imported() -> None:
    failures: list[str] = []
    modules = [info.name for info in pkgutil.walk_packages(app.__path__, prefix="app.")]

    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - on veut tout signaler
            failures.append(f"{name}: {exc!r}")

    assert not failures, "\n".join(failures)
    # Le parcours doit bien voir les sous-paquets (sinon le test ne vérifie plus rien)
    assert {"app.api.webhook", "app.services.bot", "app.schemas.whatsapp"} <= set(modules)
