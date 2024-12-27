document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("videoForm");
    const messageDiv = document.getElementById("message");
    const progressBarContainer = document.createElement("div");
    const progressBar = document.createElement("div");

    // Estilo da barra de progresso
    progressBarContainer.style.position = "relative";
    progressBarContainer.style.width = "100%";
    progressBarContainer.style.height = "20px";
    progressBarContainer.style.backgroundColor = "#e0e0e0";
    progressBarContainer.style.borderRadius = "10px";
    progressBarContainer.style.marginTop = "15px";
    progressBarContainer.style.display = "none";

    progressBar.style.width = "0%";
    progressBar.style.height = "100%";
    progressBar.style.backgroundColor = "#4caf50";
    progressBar.style.borderRadius = "10px";
    progressBar.style.transition = "width 0.3s ease";

    progressBarContainer.appendChild(progressBar);
    form.appendChild(progressBarContainer);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        messageDiv.style.display = "none";
        progressBarContainer.style.display = "block";
        progressBar.style.width = "0%";

        const formData = new FormData(form);

        try {
            const response = await fetch("/", {
                method: "POST",
                body: formData,
                headers: {
                    "Accept": "application/json"
                },
            });

            // Atualizar barra de progresso durante o upload
            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener("progress", (event) => {
                if (event.lengthComputable) {
                    const percentComplete = Math.round((event.loaded / event.total) * 100);
                    progressBar.style.width = `${percentComplete}%`;
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                const errorMessage = errorData.error || `Erro ${response.status} ao processar o vídeo.`;
                throw new Error(errorMessage);
            }

            const result = await response.json();

            messageDiv.textContent = result.message;
            messageDiv.className = "message success";
            messageDiv.style.display = "block";
            progressBar.style.width = "100%";

            if (result.download_link) {
                const link = document.createElement("a");
                link.href = result.download_link;
                link.download = ""; // Opcional: pode ser usado para nomear o arquivo.
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                console.error("Link de download não recebido na resposta:", result);
                messageDiv.textContent = "Erro: Link de download ausente.";
                messageDiv.className = "message error";
                messageDiv.style.display = "block";
            }

        } catch (error) {
            console.error("Erro durante a requisição:", error);
            messageDiv.textContent = error.message || "Ocorreu um erro inesperado.";
            messageDiv.className = "message error";
            messageDiv.style.display = "block";
        } finally {
            progressBarContainer.style.display = "none";
        }
    });
});
