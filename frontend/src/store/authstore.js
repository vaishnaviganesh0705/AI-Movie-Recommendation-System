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
    // Clear any prior user's active conversation state
    localStorage.removeItem("active_conversation_id");

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
    localStorage.removeItem("token");
    localStorage.removeItem("active_conversation_id");

    set({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  },
}));

export default useAuthStore;