import { create } from "zustand";

const useAuthStore = create((set) => ({
  user: null,

  token: localStorage.getItem("access_token"),

  isAuthenticated:
    !!localStorage.getItem("access_token"),

  login: (token, user = null) => {

    localStorage.setItem(
      "access_token",
      token
    );

    set({
      token,
      user,
      isAuthenticated: true,
    });
  },

  logout: () => {

    localStorage.removeItem(
      "access_token"
    );

    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },
}));

export default useAuthStore;