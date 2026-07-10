if __name__ == "__main__":
    root = tk.Tk()

    app = PortfolioDashboard(
        root,
        api_key="YOUR_API_KEY",
        cache_dir=Path("./cache")
    )

    root.mainloop()