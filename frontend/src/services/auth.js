import Keycloak from "keycloak-js";

const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080",
  realm: import.meta.env.VITE_KEYCLOAK_REALM || "datatutor",
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "datatutor-web",
};

export const keycloak = new Keycloak(keycloakConfig);

let initPromise = null;

export function initKeycloak() {
  if (!initPromise) {
    initPromise = keycloak
      .init({
        onLoad: "login-required",
        pkceMethod: "S256",
        checkLoginIframe: false,
      })
      .catch((err) => {
        initPromise = null;
        throw err;
      });
  }
  return initPromise;
}

export async function getValidToken() {
  if (!keycloak.authenticated) {
    await keycloak.login({ redirectUri: window.location.origin + "/" });
    return null;
  }
  try {
    await keycloak.updateToken(30);
    return keycloak.token;
  } catch (err) {
    await keycloak.login({ redirectUri: window.location.origin + "/" });
    return null;
  }
}

export function logoutUser() {
  return keycloak.logout({
    redirectUri: window.location.origin + "/",
  });
}