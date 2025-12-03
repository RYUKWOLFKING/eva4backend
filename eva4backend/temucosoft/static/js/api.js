// Configuración de la API: usa el mismo host para evitar problemas de CORS
const API_BASE_URL = `${window.location.origin.replace(/\/$/, "")}/api`;

class APIClient {
    constructor() {
        this.token = localStorage.getItem("access_token");
        this.refreshToken = localStorage.getItem("refresh_token");
    }

    // Obtener JWT
    async login(username, password) {
        const response = await fetch(`${API_BASE_URL}/token/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) throw new Error("Credenciales inválidas");

        const data = await response.json();
        localStorage.setItem("access_token", data.access);
        localStorage.setItem("refresh_token", data.refresh);
        this.token = data.access;
        this.refreshToken = data.refresh;
        return data;
    }

    // Renovar token
    async refreshAccessToken() {
        if (!this.refreshToken) {
            this.logout();
            throw new Error("No hay refresh token disponible");
        }

        const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh: this.refreshToken }),
        });

        if (!response.ok) {
            this.logout();
            throw new Error("No se pudo renovar el token");
        }

        const data = await response.json();
        localStorage.setItem("access_token", data.access);
        this.token = data.access;
        return data;
    }

    // Cerrar sesión
    logout() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        this.token = null;
        this.refreshToken = null;
        window.location.href = "/login/";
    }

    // Realizar peticiones autenticadas
    async request(endpoint, method = "GET", body = null) {
        if (!this.token) {
            this.logout();
            throw new Error("Token ausente");
        }

        const headers = {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
        };

        const options = {
            method,
            headers,
            credentials: "include",
        };

        if (body) options.body = JSON.stringify(body);

        let response = await fetch(`${API_BASE_URL}${endpoint}`, options);

        // Si el token expiró, renovarlo y reintentar
        if (response.status === 401) {
            await this.refreshAccessToken();
            headers.Authorization = `Bearer ${this.token}`;
            response = await fetch(`${API_BASE_URL}${endpoint}`, {
                ...options,
                headers,
            });
        }

        if (!response.ok) {
            // intentar mostrar el detalle devuelto por el backend
            let detail = '';
            try {
                const data = await response.json();
                detail = typeof data === 'string' ? data : JSON.stringify(data);
            } catch (_) {
                // fallback a texto plano
                try {
                    detail = await response.text();
                } catch (_) {
                    detail = '';
                }
            }
            const msg = detail ? detail : response.statusText;
            throw new Error(`Error ${response.status}: ${msg}`);
        }

        if (response.status === 204) {
            // No content, nada que parsear
            return null;
        }

        // Si no hay cuerpo, devolver null
        const text = await response.text();
        if (!text) return null;
        return JSON.parse(text);
    }

    // Métodos específicos de la API
    getProducts(page = 1) {
        return this.request(`/products/?page=${page}`);
    }

    getProduct(id) {
        return this.request(`/products/${id}/`);
    }

    getInventory() {
        return this.request("/inventory/");
    }

    getUserProfile() {
        return this.request("/profile/");
    }

    getOrders() {
        return this.request("/orders/");
    }

    createOrder(orderData) {
        return this.request("/orders/", "POST", orderData);
    }

    getSales() {
        return this.request("/sales/");
    }

    createSale(saleData) {
        return this.request("/sales/", "POST", saleData);
    }

    getSuppliers() {
        return this.request("/suppliers/");
    }

    getBranches() {
        return this.request("/branches/");
    }

    getUsers() {
        return this.request("/users/");
    }

    // Carrito
    addToCart(productId, quantity = 1) {
        return this.request("/cart/add/", "POST", { product: productId, quantity });
    }

    getCart() {
        return this.request("/cart/", "GET");
    }

    checkoutCart() {
        return this.request("/cart/checkout/", "POST", {});
    }

    isAuthenticated() {
        return Boolean(this.token);
    }
}

// Instancia global de cliente API
const apiClient = new APIClient();

// Verificar autenticación
function checkAuthentication() {
    if (!apiClient.isAuthenticated() && !window.location.pathname.includes("/login")) {
        window.location.href = "/login/";
    }
}

// Ejecutar al cargar la página
document.addEventListener("DOMContentLoaded", checkAuthentication);
