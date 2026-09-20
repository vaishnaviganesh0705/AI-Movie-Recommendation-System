import api from "./api";

export async function fetchMovies() {
  try {
    const response = await api.get("/tmdb/movies/discover");
    return response.data;
  } catch (error) {
    if (error.response && error.response.data) {
      throw new Error(error.response.data.detail);
    }
    throw error;
  }
}
