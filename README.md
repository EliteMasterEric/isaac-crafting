# Binding of Isaac Repentance - Bag of Crafting Calculator

This calculator is an updated version, modified from the ones provided by [wchill](https://github.com/wchill/bindingofisaac) and [PlatinumGod](https://platinumgod.co.uk).

## Build/Update Instructions

Perform the following steps to create a new version of the web app, which uses the latest data from the game:

### Part 1. Extract Game Data

1. Navigate to your Isaac install folder.
    - You can do this easily by opening your Steam Library, right clicking Isaac, and selecting Manage -> Browse Local Files
2. Open the `tools/ResourceExtractor` folder and run the `ResourceExtractor.exe`.
    - This will create several directories in the root Isaac folder, two directories up.
3. Grab the following files.
    - `resources-dlc3/itempools.xml`
    - `resources-dlc3/items_metadata.xml`
    - `resources-dlc3/items.xml`
    - `resources-dlc3/recipes.xml`
    - `resources/stringtable.sta`
4. Place the above files in a new directory in the `src/crafting_calculator/gamedata/pc` folder.

### Part 2. Python App Usage

You can run the python app (which provides a CLI for the calculator) locally by moving into the `src` folder and running `python -m crafting_calculator`.

Alternatively, you can run `pip install .` in the root directory of the project, then run `calculate_bag -h`.

## Additional Notes

- Item ID `64` is Steam Sale.