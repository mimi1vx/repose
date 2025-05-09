import concurrent.futures
import logging
from itertools import chain
from ..utils import blue
from .remove import Remove
from ..types import ExitCode


logger = logging.getLogger("repose.command.uninstall")


class Uninstall(Remove):
    command = True

    def _calculate_repodict(self, host, patterns):
        rdict = {}
        for pattern in patterns:
            for repo in self.targets[host].repos.items():
                if pattern in repo[0]:
                    if repo[1].name in rdict:
                        rdict[repo[1].name].append(repo[0])
                    else:
                        rdict[repo[1].name] = [repo[0]]
        return rdict

    def _run(self, orepa, host):
        patterns = self._calculate_pattern(orepa, host)
        if not patterns:
            logger.info("For %s no products for remove found", host)
            return

        rdict = self._calculate_repodict(host, patterns)
        if not rdict:
            logger.info("For %s no repos for remove found", host)
            rrcmd = False
        else:
            rrcmd = self.rrcmd.format(
                repos=" ".join(chain.from_iterable(rdict.values()))
            )

        transactional = False
        if "SL-Micro" in patterns:
            transactional = True
            pdcmd = self.rrpdtcmd.format(
                prodcuts=" ".join(x.split(":")[0] for x in patterns)
            )
        else:
            pdcmd = self.rrpcmd.format(
                products=" ".join(x.split(":")[0] for x in patterns)
            )

        if self.dryrun:
            if rrcmd:
                print(blue(host) + " - {}".format(rrcmd))
            print(blue(host) + " - {}".format(pdcmd))
        else:
            if rrcmd:
                self.targets[host].run(rrcmd)
                self._report_target(host)
            self.targets[host].run(pdcmd)
            self._report_target(host)
            if transactional:
                logger.info("Reboot %s to switch into updated snapshot", host)

    def run(self) -> ExitCode:
        self.targets.read_repos()
        self.targets.parse_repos()
        orepa = []

        for r in self.repa:
            r.repo = None
            orepa.append(r)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            targets = [
                executor.submit(self._run, orepa, target)
                for target in self.targets.keys()
            ]
            concurrent.futures.wait(targets)

        self.targets.close()
        return 0
