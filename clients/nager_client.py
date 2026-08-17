import httpx
from exceptions import HolidayApiError






class NagerHolidayClient:


    def __init__(self, base_url: str):
        """ Constructeur """
        self._base_url = base_url
        self._cache: dict[tuple[str, int], list[dict]] = {}



    async def get_public_holidays(self, pays_code: str, annee: int) -> list[dict]:
        """ Récupération des congés par pays dans l'API Nager. """
        pays_code = pays_code.strip().upper()
        key = (pays_code, annee)
        if key in self._cache:
            return self._cache[key]

        url = f"{self._base_url}/{annee}/{pays_code}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                raise HolidayApiError(f"Code pays invalide ou API indisponible ({e.response.status_code})") from e
            except httpx.RequestError as e:
                raise HolidayApiError("Impossible de joindre l'API des jours fériés") from e

        self._cache[key] = data
        return data

