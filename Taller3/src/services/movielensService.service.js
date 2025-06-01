class MovielensService {
    constructor() {
        this.maxUserId = null;
        this.isLoading = false;
    }

    async getMaxUserId() {
        if (this.maxUserId !== null) {
            return this.maxUserId;
        }

        if (this.isLoading) {
            while (this.isLoading) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            return this.maxUserId;
        }

        this.isLoading = true;

        try {
            const response = await fetch('./src/data/ratings.csv');
            
            if (!response.ok) {
                throw new Error('No se pudo cargar ratings.csv');
            }

            const csvText = await response.text();
            const lines = csvText.split('\n');
            
            let maxId = 0;
            
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line) {
                    const userId = parseInt(line.split(',')[0]);
                    if (!isNaN(userId) && userId > maxId) {
                        maxId = userId;
                    }
                }
            }

            this.maxUserId = maxId;
            return maxId;

        } catch (error) {
            console.error('Error:', error);
            // Fallback para MovieLens Latest Small
            this.maxUserId = 610;
            return 610;
        } finally {
            this.isLoading = false;
        }
    }
}

export const movielensService = new MovielensService();
export default movielensService;