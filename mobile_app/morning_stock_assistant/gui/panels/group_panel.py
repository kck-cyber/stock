"""
Group Panel

Morning Stock Assistant Pro
"""

import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox


class GroupPanel(tk.Frame):

    def __init__(
        self,
        master,
        watchlist_manager,
        on_select=None,
    ):

        super().__init__(master)

        self.watchlist = watchlist_manager
        self.on_select = on_select

        tk.Label(
            self,
            text="관심종목 그룹",
            font=("맑은고딕", 11, "bold")
        ).pack(pady=(0, 5))

        self.group_list = tk.Listbox(
            self,
            width=18,
            height=18,
            exportselection=False
        )

        self.group_list.pack(
            fill="both",
            expand=True
        )

        self.group_list.bind(
            "<<ListboxSelect>>",
            self._group_selected
        )

        tk.Button(
            self,
            text="+ 그룹",
            command=self.add_group
        ).pack(fill="x", pady=(5, 0))

        tk.Button(
            self,
            text="이름 변경",
            command=self.rename_group
        ).pack(fill="x")

        tk.Button(
            self,
            text="삭제",
            command=self.delete_group
        ).pack(fill="x")

        self.refresh()

    # ---------------------------------

    def refresh(self):

        self.group_list.delete(0, tk.END)

        groups = self.watchlist.get_groups()

        if isinstance(groups, dict):
            groups = groups.keys()

        for name in groups:
            self.group_list.insert(tk.END, name)

    # ---------------------------------

    def current_group(self):

        sel = self.group_list.curselection()

        if not sel:
            return None

        return self.group_list.get(sel[0])

    # ---------------------------------

    def _group_selected(self, event):

        if self.on_select:

            self.on_select(self.current_group())

    # ---------------------------------

    def add_group(self):

        name = simpledialog.askstring(
            "그룹 추가",
            "그룹명을 입력하세요."
        )

        if not name:
            return

        name = name.strip()

        if not name:
            return

        if not self.watchlist.add_group(name):

            messagebox.showwarning(
                "중복",
                "이미 존재하는 그룹입니다."
            )

            return

        self.refresh()

    # ---------------------------------

    def rename_group(self):

        old_name = self.current_group()

        if not old_name:
            return

        new_name = simpledialog.askstring(
            "이름 변경",
            "새 그룹명을 입력하세요.",
            initialvalue=old_name
        )

        if not new_name:
            return

        new_name = new_name.strip()

        if not new_name:
            return

        if not self.watchlist.rename_group(
            old_name,
            new_name
        ):

            messagebox.showwarning(
                "오류",
                "이름을 변경할 수 없습니다."
            )

            return

        self.refresh()

    # ---------------------------------

    def delete_group(self):

        name = self.current_group()

        if not name:
            return

        if not messagebox.askyesno(
            "삭제",
            f"{name} 그룹을 삭제하시겠습니까?"
        ):
            return

        self.watchlist.delete_group(name)

        self.refresh()