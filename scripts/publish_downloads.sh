#!/usr/bin/env bash
# Construit le paquet .deb et le publie dans les releases de nouhailler/huggor-downloads,
# avec le fichier .sha256 attendu par install.sh de ce dépôt.
#
# Usage : scripts/publish_downloads.sh X.Y.Z [--yes]
# Nécessite : gh (authentifié), dpkg-deb, sha256sum.

set -Eeuo pipefail

readonly DOWNLOADS_REPOSITORY="nouhailler/huggor-downloads"

version="${1:-}"
assume_yes=false
[[ "${2:-}" == "--yes" ]] && assume_yes=true
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || { echo "Usage : $0 X.Y.Z [--yes]" >&2; exit 1; }

for command_name in gh dpkg-deb sha256sum python3; do
    command -v "$command_name" >/dev/null 2>&1 \
        || { echo "Commande requise introuvable : ${command_name}" >&2; exit 1; }
done

cd "$(dirname "$0")/.."
python3 scripts/build_deb.py --version "$version"

package="dist/hf-explorer_${version}_all.deb"
(cd dist && sha256sum "$(basename "$package")" >"$(basename "$package").sha256")

echo "Paquet : ${package}"
cat "${package}.sha256"

if [[ "$assume_yes" != true ]]; then
    read -r -p "Publier la release v${version} sur ${DOWNLOADS_REPOSITORY} ? [o/N] " answer
    [[ "$answer" =~ ^[oOyY]$ ]] || { echo "Annulé."; exit 1; }
fi

gh release create "v${version}" "$package" "${package}.sha256" \
    --repo "$DOWNLOADS_REPOSITORY" \
    --title "HF Explorer ${version}" \
    --notes "Paquet Debian/Ubuntu (indépendant de l'architecture). Installation : voir le README."
