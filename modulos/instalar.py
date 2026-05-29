"""
Script de instalação offline — Sistema de Escala FAB
=====================================================
Execute este script no servidor (sem internet) para criar o ambiente virtual
e instalar todas as dependências a partir dos arquivos desta pasta.

Pré-requisitos no servidor de destino (Ubuntu/Debian):
  - Python 3.10+ instalado
  - pip instalado
  - Bibliotecas de sistema para o python-ldap:

      sudo apt-get install -y libldap2-dev libsasl2-dev python3-dev build-essential

    (Necessário apenas para compilar o python-ldap a partir do fonte .tar.gz)

Uso:
  python3 instalar.py
"""

import os
import sys
import shutil
import subprocess
import venv
from pathlib import Path

PASTA_MODULOS = Path(__file__).parent.resolve()
PASTA_PROJETO = PASTA_MODULOS.parent.resolve()
VENV_DIR = PASTA_PROJETO / ".venv"

PYTHON_MIN = (3, 10)

# Pacotes que vêm como .tar.gz (fonte) e precisam ser compilados
PACOTES_FONTE = ["python_ldap", "python-ldap"]


def verificar_python():
    v = sys.version_info[:2]
    if v < PYTHON_MIN:
        sys.exit(
            f"[ERRO] Python {'.'.join(map(str, PYTHON_MIN))}+ é necessário. "
            f"Versão atual: {sys.version}"
        )
    print(f"[OK] Python {sys.version.split()[0]}")


def verificar_dependencias_sistema():
    """Verifica se as bibliotecas de sistema para o python-ldap estão disponíveis."""
    print("\n[INFO] Verificando dependências de sistema para python-ldap...")
    tem_ldap = shutil.which("ldapsearch") is not None or Path("/usr/include/ldap.h").exists() or Path("/usr/include/x86_64-linux-gnu/ldap.h").exists()
    if not tem_ldap:
        print("""
[AVISO] Bibliotecas de sistema para python-ldap não encontradas.
        Execute antes de continuar:

            sudo apt-get install -y libldap2-dev libsasl2-dev python3-dev build-essential

        Depois rode este script novamente.
""")
        resposta = input("Deseja continuar mesmo assim? (s/N): ").strip().lower()
        if resposta != "s":
            sys.exit("[CANCELADO] Instale as dependências e rode novamente.")
    else:
        print("[OK] Dependências de sistema para LDAP encontradas.")


def criar_venv():
    if VENV_DIR.exists():
        print(f"[INFO] Ambiente virtual já existe em: {VENV_DIR}")
        return
    print(f"[INFO] Criando ambiente virtual em: {VENV_DIR}")
    venv.create(str(VENV_DIR), with_pip=True)
    print("[OK] Ambiente virtual criado.")


def pip_venv():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def instalar_wheels():
    pip = pip_venv()
    wheels = sorted(PASTA_MODULOS.glob("*.whl"))
    if not wheels:
        print("[AVISO] Nenhum arquivo .whl encontrado — pulando wheels.")
        return

    print(f"\n[INFO] Instalando {len(wheels)} pacote(s) .whl:")
    for w in wheels:
        print(f"       {w.name}")

    cmd = [
        str(pip), "install",
        "--no-index",
        "--find-links", str(PASTA_MODULOS),
        *[str(w) for w in wheels],
    ]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("[ERRO] Falha na instalação dos pacotes .whl.")
    print("[OK] Pacotes .whl instalados.")


def instalar_fontes():
    """Instala pacotes distribuídos como .tar.gz (requer compilação)."""
    pip = pip_venv()
    tarballs = sorted(PASTA_MODULOS.glob("*.tar.gz"))
    if not tarballs:
        return

    print(f"\n[INFO] Compilando e instalando {len(tarballs)} pacote(s) fonte (.tar.gz):")
    for t in tarballs:
        print(f"       {t.name}")
        cmd = [str(pip), "install", "--no-index", str(t)]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            sys.exit(
                f"\n[ERRO] Falha ao compilar {t.name}.\n"
                "Certifique-se de que as bibliotecas de sistema estão instaladas:\n"
                "    sudo apt-get install -y libldap2-dev libsasl2-dev python3-dev build-essential"
            )
    print("[OK] Pacotes fonte compilados e instalados.")


def mostrar_proximos_passos():
    if os.name == "nt":
        ativar = rf"{VENV_DIR}\Scripts\activate"
        python_venv = rf"{VENV_DIR}\Scripts\python.exe"
    else:
        ativar = f"source {VENV_DIR}/bin/activate"
        python_venv = f"{VENV_DIR}/bin/python"

    pacotes_whl = [w.stem for w in sorted(PASTA_MODULOS.glob("*.whl"))]
    pacotes_tgz = [t.name for t in sorted(PASTA_MODULOS.glob("*.tar.gz"))]
    todos = pacotes_whl + pacotes_tgz

    print(f"""
=======================================================
 INSTALAÇÃO CONCLUÍDA
=======================================================

Próximos passos para iniciar o sistema:

1. Ativar o ambiente virtual:
   {ativar}

2. Aplicar as migrações do banco de dados (primeiro uso):
   {python_venv} manage.py migrate --noinput

3. Criar o superusuário (primeiro uso):
   {python_venv} manage.py createsuperuser

4. (Opcional) Popular dados de exemplo:
   {python_venv} manage.py seed_dados

5. Iniciar o servidor de desenvolvimento:
   {python_venv} manage.py runserver 0.0.0.0:8000

   -- OU em produção com Gunicorn --
   {VENV_DIR}/bin/gunicorn --bind 0.0.0.0:8000 --workers 3 core.wsgi:application

6. Coletar arquivos estáticos (produção/Gunicorn):
   {python_venv} manage.py collectstatic --noinput

=======================================================
 Pacotes instalados ({len(todos)}):
""")
    for p in todos:
        print(f"   • {p}")
    print("=======================================================")


def main():
    print("=" * 55)
    print(" Instalador Offline — Sistema de Escala FAB")
    print("=" * 55)
    verificar_python()
    verificar_dependencias_sistema()
    criar_venv()
    instalar_wheels()
    instalar_fontes()
    mostrar_proximos_passos()


if __name__ == "__main__":
    main()
