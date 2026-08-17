from datetime import date, datetime, timedelta
from repositories.employee_repository import EmployeeRepository
from clients.nager_client import NagerHolidayClient
from exceptions import EmployeeNotFoundError, HolidayApiError
from models.leave_calculation import LeaveCalculation






class LeaveService:


    def __init__(self, employee_repo: EmployeeRepository, holiday_client: NagerHolidayClient):
        """ Constructeur """
        self._employee_repo = employee_repo
        self._holiday_client = holiday_client



    async def calculer_jours_ouvres(self, nom: str, debut: date, fin: date) -> LeaveCalculation:
        """ Calcul des jours ouvrés """
        employe = self._employee_repo.find_by_name(nom)
        if employe is None:
            raise EmployeeNotFoundError(nom)

        pays_code = employe.pays_code or "FR"
        feries_dates: set[date] = set()
        avertissement = None

        for annee in range(debut.year, fin.year + 1):
            try:
                feries = await self._holiday_client.get_public_holidays(pays_code, annee)
            except HolidayApiError as e:
                avertissement = str(e)
                continue
            for jour in feries:
                try:
                    feries_dates.add(datetime.strptime(jour["date"], "%Y-%m-%d").date())
                except (KeyError, ValueError):
                    continue

        jours_ouvres, feries_dans_periode = self._compter_jours_ouvres(debut, fin, feries_dates)

        solde_avant = employe.solde_conges_jours
        solde_apres = (solde_avant - jours_ouvres) if solde_avant is not None else None

        return LeaveCalculation(
            employee_name=employe.name, pays_code=pays_code, debut=debut, fin=fin,
            jours_ouvres=jours_ouvres, jours_feries=feries_dans_periode,
            solde_avant=solde_avant, solde_apres=solde_apres, avertissement=avertissement,
        )



    @staticmethod
    def _compter_jours_ouvres(debut: date, fin: date, feries: set[date]) -> tuple[int, list[date]]:
        jours_ouvres = 0
        feries_dans_periode = []
        jour = debut
        while jour <= fin:
            if jour in feries:
                feries_dans_periode.append(jour)
            elif jour.weekday() < 5:
                jours_ouvres += 1
            jour += timedelta(days=1)
        return jours_ouvres, feries_dans_periode
