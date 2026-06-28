import tkinter as tk
from tkinter import messagebox
import webbrowser
import requests

# ======================
# CONFIGURATION
# ======================
API_LOGIN_URL = "http://127.0.0.1:8000/api/login/"      # Django login API
SIGNUP_PAGE_URL = "http://localhost:5173/auth/signup"        # Django signup webpage

# ======================
# LOGIN WINDOW
# ======================
class LoginApp:
    def __init__(self, root):
        self.root = root
        root.title("Login")
        root.geometry("350x260")
        root.resizable(False, False)

        # Title
        tk.Label(root, text="Welcome", font=("Arial", 18, "bold")).pack(pady=10)

        # Username
        tk.Label(root, text="Username").pack()
        self.username_entry = tk.Entry(root, width=30)
        self.username_entry.pack(pady=5)

        # Password
        tk.Label(root, text="Password").pack()
        self.password_entry = tk.Entry(root, show="*", width=30)
        self.password_entry.pack(pady=5)

        # Login button
        tk.Button(root, text="Login", width=15, command=self.login).pack(pady=15)

        # Signup button
        tk.Button(root, text="Create New Account", width=20, command=self.open_signup).pack()

    # ======================
    # OPEN DJANGO SIGNUP PAGE
    # ======================
    def open_signup(self):
        webbrowser.open(SIGNUP_PAGE_URL)

    # ======================
    # LOGIN REQUEST
    # ======================
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return

        try:
            payload = {
                "username": username,
                "password": password
            }

            response = requests.post(API_LOGIN_URL, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                token = data.get("token")  # adjust to your API's token name

                if not token:
                    messagebox.showerror("Error", "No token returned by server")
                    return
                print(token['access'])
                messagebox.showinfo("Success","Login Successful!",)
                self.root.destroy()
                open_main_window(token)

            else:
                try:
                    msg = response.json().get("detail", "Invalid credentials")
                except:
                    msg = "Invalid login"
                messagebox.showerror("Login Failed", msg)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not reach server\n{e}")

# ======================
# MAIN WINDOW AFTER LOGIN
# ======================
def open_main_window(token):
    main = tk.Tk()
    main.title("Dashboard")
    main.geometry("400x200")

    tk.Label(main, text="You are logged in!", font=("Arial", 16)).pack(pady=20)
    tk.Label(main, text=f"Token: {token[:30]}...", fg="gray").pack()

    tk.Button(main, text="Start Next Process", command=lambda: next_process(token)).pack(pady=20)

    main.mainloop()

# ======================
# NEXT PROCESS (You can customize)
# ======================
def next_process(token):
    messagebox.showinfo("Process", "Running next step...")
    # Example API call with token
    # requests.get("http://127.0.0.1:8000/api/start/", headers={"Authorization": f"Bearer {token}"})

# ======================
# RUN APP
# ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()
