# ORCID and Publication Cleaner

This project was developed for use with the [Neotoma Paleoecology Database](https://www.neotomadb.org) to support better integration of external data for individuals and publications within the data infrastructure of Neotoma itself.

The goal of this project is to support manual editing of publication and contact information within Neotoma using a simple user interface that helps users quickly see article and author metadata, and then accept, or reject neccessary changes.

The program directly interacts with the [Neotoma API](https://api.neotomadb.org) as well as the [OpenAlex API](https://openalex.org/) using a Python/flask framework.

## Contributors

* [Dev Paul](https://www.linkedin.com/in/devpaul-1-)

## Getting Started

### Installing Packages

This project uses `uv` as a package manager. A user cloning this repository for the first time should [install `uv`](https://docs.astral.sh/uv/getting-started/installation/) either using `pip` or using one of the other instruction sets on the `uv` website.

Once `uv` is installed you can execute the following:

```bash
uv pip install .
```

This will build the package and install all the required packages as identified in `pyproject.toml`.

### Running the Application

Once the required packages are installed, you can run the development server using the command:

```bash
uv run -- flask run -p 5000
```

This will launch the development server locally on port `5000`, and it can be accessed from `http://127.0.0.1:5000` or using `http://localhost:5000`
